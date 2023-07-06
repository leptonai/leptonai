// Package get implements get command.
package get

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"sort"
	"syscall"
	"time"

	"github.com/olekukonko/tablewriter"
	"github.com/opencost/opencost/pkg/kubecost"
	"github.com/spf13/cobra"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"

	"github.com/leptonai/lepton/go-pkg/k8s/service"
)

var (
	kubeconfigPath string

	opencostNamespace string
	opencostSvcName   string
	opencostSvcPort   int

	queryPath       string
	queryAgg        string
	queryWindow     string
	queryAccumulate bool

	queryRounds   uint
	queryInterval time.Duration

	syncToDB bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get metering data from kubecost/opencost",
		Long: `
# simpler version of "kubectl-cost"
kubectl cost pod \
--service-port 9003 \
--service-name cost-analyzer-cost-analyzer \
--kubecost-namespace kubecost \
--allocation-path /allocation/compute  \
--window 5m \
--show-efficiency=false

# for example
mothership metering get --kubeconfig /tmp/gh82.kubeconfig
`,
		Run: getFunc,
	}

	cmd.PersistentFlags().StringVarP(&kubeconfigPath, "kubeconfig", "k", "", "Kubeconfig path (otherwise, client uses the one from KUBECONFIG env var)")
	cmd.PersistentFlags().StringVarP(&opencostNamespace, "opencost-namespace", "n", "kubecost", "Namespace where opencost/kubecost is running")
	cmd.PersistentFlags().StringVarP(&opencostSvcName, "opencost-service-name", "s", "cost-analyzer-cost-analyzer", "Service name of opencost/kubecost to port-forward")
	cmd.PersistentFlags().IntVarP(&opencostSvcPort, "opencost-service-port", "t", 9003, "Service port of opencost/kubecost")

	// ref. https://docs.kubecost.com/apis/apis-overview/allocation#querying
	cmd.PersistentFlags().StringVar(&queryPath, "query-path", "/allocation/compute", "Query path")
	cmd.PersistentFlags().StringVar(&queryAgg, "query-aggregate", "cluster,namespace,pod", "Query aggregate")
	cmd.PersistentFlags().StringVar(&queryWindow, "query-window", "5m", "Query window duration")
	cmd.PersistentFlags().BoolVar(&queryAccumulate, "query-accumulate", true, "Configure accumulate (If false, query-window=3d results in three different 24-hour periods. If true, the results are accumulated into one entire window.)")

	cmd.PersistentFlags().UintVar(&queryRounds, "query-rounds", 1, "Number of query rounds to perform, set to 0 to poll indefinitely")
	cmd.PersistentFlags().DurationVar(&queryInterval, "query-interval", 10*time.Minute, "Query interval")

	cmd.PersistentFlags().BoolVar(&syncToDB, "sync-to-db", false, "Must be set true to enable sync to backend database")

	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
	kubeconfig := os.Getenv("KUBECONFIG")
	if kubeconfigPath != "" {
		kubeconfig = kubeconfigPath
	}
	log.Printf("loading kubeconfig %q", kubeconfig)

	kcfg, err := clientcmd.LoadFromFile(kubeconfig)
	if err != nil {
		log.Fatalf("failed to load kubeconfig %v", err)
	}
	clusterARN := ""
	for k := range kcfg.Clusters {
		clusterARN = k
		break
	}

	// Load Kubernetes configuration from default location or specified kubeconfig file
	restConfig, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		log.Fatalf("failed to build config from kubeconfig %v", err)
	}

	// Create a Kubernetes client
	clientset, err := kubernetes.NewForConfig(restConfig)
	if err != nil {
		log.Fatal(err)
	}

	// ref. https://github.com/kubecost/kubectl-cost/blob/main/pkg/cmd/aggregatedcommandbuilder.go
	// ref. https://github.com/kubecost/kubectl-cost/blob/main/pkg/query/allocation.go
	// ref. https://github.com/kubecost/kubectl-cost/blob/main/pkg/query/portforward.go
	fwd, err := service.NewPortForwardQuerier(
		context.Background(),
		clientset,
		restConfig,
		opencostNamespace,
		opencostSvcName,
		opencostSvcPort,
	)
	if err != nil {
		log.Fatalf("failed to create port forwarder for service %v", err)
	}
	defer fwd.Stop()

	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGTERM, syscall.SIGINT)

	log.Printf("starting get for %d rounds with %v interval", queryRounds, queryInterval)
	for i := uint(0); i < queryRounds; i++ {
		if i > 0 {
			select {
			case sig := <-sigs:
				log.Printf("received OS signal %v -- returning", sig)
				return
			case <-time.After(queryInterval):
			}
		}

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		queryRs, err := fwd.QueryGet(
			ctx,
			queryPath,
			map[string]string{
				"window":           queryWindow,
				"aggregate":        queryAgg,
				"accumulate":       fmt.Sprintf("%v", queryAccumulate),
				"filterNamespaces": "",
			},
		)
		cancel()
		if err != nil {
			log.Fatalf("failed to proxy get kubecost %v", err)
		}

		var ar allocationResponse
		if err = json.Unmarshal(queryRs, &ar); err != nil {
			log.Fatalf("failed to parse allocation response %v", err)
		}

		data := make([]rawData, 0, len(ar.Data))
		for _, a := range ar.Data {
			for _, v := range a {
				// v.Name is same as key in the map
				// v.Name is [cluster name]/[namespace]/[pod id]
				// v.Properties.ProviderID is the instance ID in AWS
				// v.Properties.Cluster is hard-coded as "cluster-one", do not use this

				// ignore the resource usage by "kubecost" itself
				if v.Properties.Namespace == "kubecost" {
					continue
				}

				d := rawData{
					Cluster:   clusterARN,
					Namespace: v.Properties.Namespace,
					PodID:     v.Properties.Pod,

					Start:          v.Start.Unix(),
					End:            v.End.Unix(),
					RunningMinutes: v.Minutes(),
					Window:         v.Window.Duration().String(),

					CPUCoreHours: v.CPUCoreHours,
					GPUHours:     v.GPUHours,
				}
				data = append(data, d)
			}
		}
		log.Printf("total %d data", len(data))

		sort.SliceStable(data, func(i, j int) bool {
			if data[i].Namespace == data[j].Namespace {
				return data[i].PodID < data[j].PodID
			}
			return data[i].Namespace < data[j].Namespace
		})
		rows := make([][]string, 0, len(data))
		for _, d := range data {
			rows = append(rows, d.toTableRow())
		}

		buf := bytes.NewBuffer(nil)
		tb := tablewriter.NewWriter(buf)
		tb.SetAutoWrapText(false)
		tb.SetAlignment(tablewriter.ALIGN_LEFT)
		tb.SetCenterSeparator("*")
		tb.SetHeader(tableColumns)
		tb.AppendBulk(rows)
		tb.Render()
		fmt.Println(buf.String())

		if !syncToDB {
			log.Print("skipping sync")
			return
		}

		log.Printf("syncing %d rows to database", len(data))
		// TODO: implement sync to database
	}
}

type allocationResponse struct {
	Code int                              `json:"code"`
	Data []map[string]kubecost.Allocation `json:"data"`
}

var tableColumns = []string{
	"cluster",
	"namespace",
	"pod id",

	"start",
	"end",
	"running minutes",
	"window",

	"cpu core hours",
	"gpu hours",
}

type rawData struct {
	Cluster   string
	Namespace string
	PodID     string

	Start          int64
	End            int64
	RunningMinutes float64
	Window         string

	// Cumulative CPU core-hours allocated.
	// Number of cores multipled by the number of hours.
	// Under the hood, it uses "container_cpu_allocation",
	// the average number of CPUs requested/used over last 1m,
	// to aggregate in hours.
	CPUCoreHours float64
	// Cumulative GPU-hours allocated.
	// Number of GPU counts multipled by the number of hours.
	// Under the hood, it uses "container_gpu_allocation".
	GPUHours float64
}

func (d rawData) toTableRow() []string {
	return []string{
		d.Cluster,
		d.Namespace,
		d.PodID,

		fmt.Sprintf("%d", d.Start),
		fmt.Sprintf("%d", d.End),
		fmt.Sprintf("%.5f", d.RunningMinutes),
		d.Window,

		fmt.Sprintf("%.5f", d.CPUCoreHours),
		fmt.Sprintf("%.5f", d.GPUHours),
	}
}
