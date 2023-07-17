package sync

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/go-pkg/metering"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/spf13/cobra"
	"k8s.io/client-go/kubernetes"
)

var (
	kubeconfigPath string

	opencostNamespace string
	opencostSvcName   string
	opencostSvcPort   int

	queryPath       string
	queryAgg        string
	queryResolution string
	syncInterval    int
)

func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "sync",
		Short: "Automated syncing of metering data from kubecost/opencost to interval-based metering db",
		Long: `
# Sync metering data from kubecost/opencost indefinitely to interval-based metering db
By default, we sync every 10th minute (i.e 10:00, 10:10, 10:20, etc) in 10 minute intervals
query-window should evenly divide 60, e.g 10m, 15m, 20m, 30m, 60m 
and recommended to be at least 5 minutes.
`,

		Run: syncFunc,
	}

	cmd.PersistentFlags().StringVarP(&kubeconfigPath, "kubeconfig", "k", "", "Kubeconfig path (otherwise, client uses the one from KUBECONFIG env var)")
	cmd.PersistentFlags().StringVarP(&opencostNamespace, "opencost-namespace", "n", "kubecost", "Namespace where opencost/kubecost is running")
	cmd.PersistentFlags().StringVarP(&opencostSvcName, "opencost-service-name", "s", "cost-analyzer-cost-analyzer", "Service name of opencost/kubecost to port-forward")
	cmd.PersistentFlags().IntVarP(&opencostSvcPort, "opencost-service-port", "t", 9003, "Service port of opencost/kubecost")

	// ref. https://docs.kubecost.com/apis/apis-overview/allocation#querying
	cmd.PersistentFlags().StringVar(&queryPath, "query-path", "/allocation/compute", "Query path")
	cmd.PersistentFlags().StringVar(&queryAgg, "query-aggregate", "cluster,namespace,pod", "Query aggregate")
	cmd.PersistentFlags().StringVar(&queryResolution, "query-resolution", "1m", "Query resolution")
	cmd.PersistentFlags().IntVar(&syncInterval, "sync-interval-in-minutes", 10, "Interval to sync data to db")

	return cmd
}

func syncFunc(cmd *cobra.Command, args []string) {
	if 60%syncInterval != 0 {
		log.Fatalf("Invalid sync interval (must be a factor of 60, eg. 5, 10, etc): %d", syncInterval)
	}
	// create aurora db connection
	auroraCfg := common.ReadAuroraConfigFromFlag(cmd)
	db, err := auroraCfg.NewHandler()
	if err != nil {
		log.Fatalf("failed to connect to db %v", err)
	}
	aurora := metering.AuroraDB{DB: db}
	defer aurora.DB.Close()
	log.Printf("Database connection established")

	kubeconfig := os.Getenv("KUBECONFIG")
	if kubeconfigPath != "" {
		kubeconfig = kubeconfigPath
	}
	// build rest config
	restConfig, clusterARN, err := common.BuildRestConfig(kubeconfig)
	if err != nil {
		log.Fatalf("failed to build rest config %v", err)
	}
	// build k8s clientset
	clientset, err := kubernetes.NewForConfig(restConfig)
	if err != nil {
		log.Fatalf("failed to build k8s clientset %v", err)
	}
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

	syncDuration := time.Duration(syncInterval) * time.Minute
	ticker := time.NewTicker(10 * time.Second)
	for range ticker.C {
		select {
		case <-sigs:
			ticker.Stop()
			return
		default:
			now := time.Now()
			_, lastRunTime, err := metering.GetMostRecentFineGrainEntry(aurora)
			if err != nil {
				log.Fatalf("failed to get most recent query time %v", err)
			}
			lastRunExists := !lastRunTime.IsZero()

			currMinute := now.Minute()
			diff := now.Sub(lastRunTime)
			if currMinute%syncInterval == 0 && (diff > syncDuration || !lastRunExists) {
				queryEnd := time.Date(now.Year(), now.Month(), now.Day(), now.Hour(), currMinute, 0, 0, now.Location())
				queryStart := queryEnd.Add(-1 * syncDuration)
				log.Printf("Syncing with window query start: %s, query end: %s", queryStart, queryEnd)
				syncOnce(queryStart, queryEnd, aurora, clientset, fwd, clusterARN, cmd)
			} else {
				if !lastRunExists {
					log.Print("Skipping sync: syncing on % minute intervals, no previous sync found")
				} else {
					log.Printf("Skipping sync, time since last run time: %s", diff.Round(time.Second))
				}
			}
		}
	}
}

func syncOnce(start time.Time, end time.Time, aurora metering.AuroraDB, clientset *kubernetes.Clientset, fwd *service.PortForwardQuerier, clusterARN string, cmd *cobra.Command) {
	qp := metering.OcQueryParams{
		ClusterARN:         clusterARN,
		QueryPath:          queryPath,
		QueryAgg:           queryAgg,
		QueryAcc:           false,
		QueryResolution:    queryResolution,
		QueryStart:         start,
		QueryEnd:           end,
		ExcludedNamespaces: metering.ExcludedNamespaces,
	}

	data, err := metering.GetFineGrainData(clientset, fwd, qp)
	if err != nil {
		log.Fatalf("failed to get data %v", err)
	}

	// create a new connection each time (in case token/connections expire between syncs)
	err = metering.SyncToDB(aurora, data)
	if err != nil {
		log.Printf("Data sync failed for window %s, %s: %v", start.Format(time.ANSIC), end.Format(time.ANSIC), err)
	}
}
