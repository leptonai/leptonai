// Package get implements get command.
package get

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/spf13/cobra"
	"k8s.io/client-go/kubernetes"

	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/go-pkg/metering"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
)

var (
	kubeconfigPath string

	opencostNamespace string
	opencostSvcName   string
	opencostSvcPort   int

	queryPath       string
	queryAgg        string
	queryWindow     string
	queryResolution string
	queryAccumulate bool

	queryRounds   uint
	queryInterval time.Duration

	syncToDB bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership metering get" command.
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
	cmd.PersistentFlags().StringVar(&queryResolution, "query-resolution", "1m", "Query resolution")
	cmd.PersistentFlags().BoolVar(&queryAccumulate, "query-accumulate", true, "Configure accumulate (If false, query-window=3d results in three different 24-hour periods. If true, the results are accumulated into one entire window.)")

	cmd.PersistentFlags().UintVar(&queryRounds, "query-rounds", 1, "Number of query rounds to perform, set to 0 to poll indefinitely")
	cmd.PersistentFlags().DurationVar(&queryInterval, "query-interval", 10*time.Minute, "Query interval")

	// aurora db related flags
	cmd.PersistentFlags().BoolVar(&syncToDB, "sync-to-db", false, "Must be set true to enable sync to backend database")
	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
	kubeconfig := os.Getenv("KUBECONFIG")
	if kubeconfigPath != "" {
		kubeconfig = kubeconfigPath
	}
	restConfig, clusterARN, err := common.BuildRestConfig(kubeconfig)
	if err != nil {
		log.Fatalf("error building config from kubeconfig %v", err)
	}

	qp := metering.OcQueryParams{
		ClusterARN:         clusterARN,
		QueryPath:          queryPath,
		QueryAgg:           queryAgg,
		QueryAcc:           queryAccumulate,
		QueryResolution:    queryResolution,
		QueryWindow:        queryWindow,
		QueryRounds:        queryRounds,
		QueryInterval:      queryInterval,
		ExcludedNamespaces: metering.ExcludedNamespaces,
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

	log.Printf("starting get for %d rounds with %v interval", qp.QueryRounds, qp.QueryInterval)
	for i := uint(0); i < queryRounds; i++ {
		if i > 0 {
			select {
			case sig := <-sigs:
				log.Printf("received OS signal %v -- returning", sig)
				return
			case <-time.After(queryInterval):
			}
		}

		data, err := metering.GetFineGrainData(clientset, fwd, qp)
		if err != nil {
			log.Fatalf("failed to get data %v", err)
		}
		log.Printf("total %d data", len(data))
		metering.PrettyPrint(data)

		var podData []metering.PodInfo
		for _, d := range data {
			podInfo := metering.PodInfo{
				Namespace:            d.Namespace,
				LeptonDeploymentName: d.LeptonDeploymentName,
				Shape:                d.PodShape,
				PodName:              d.PodName,
			}
			podData = append(podData, podInfo)
		}
		log.Printf("total %d pod data", len(podData))
		if !syncToDB {
			log.Print("skipping sync")
			return
		}

		auroraCfg := common.ReadAuroraConfigFromFlag(cmd)
		err = metering.SyncToDB(auroraCfg, "fine_grain", data, "pods", podData)
		if err != nil {
			log.Fatalf("failed to sync to db %v", err)
		}
	}
}
