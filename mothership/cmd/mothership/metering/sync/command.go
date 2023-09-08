package sync

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/go-pkg/metering"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/spf13/cobra"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

var (
	kubeconfigPath string

	opencostNamespace string
	opencostSvcName   string
	opencostSvcPort   int

	prometheusNamespace string
	prometheusSvcName   string
	prometheusSvcPort   int

	mothershipRegion string

	queryPath       string
	queryAgg        string
	queryResolution string
	syncInterval    int

	enableStorage bool
	enableCompute bool

	inCluster   bool
	clusterName string

	listenPort int
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

--enable-compute and --enable-storage flags can be used to enable syncing compute and storage data respectively. At least one must be set.
`,

		Run: syncFunc,
	}

	cmd.PersistentFlags().StringVarP(&kubeconfigPath, "kubeconfig", "k", "", "Kubeconfig path (otherwise, client uses the one from KUBECONFIG env var)")

	// required for compute data sync
	cmd.PersistentFlags().StringVar(&opencostNamespace, "opencost-namespace", "kubecost-cost-analyzer", "Namespace where opencost/kubecost is running")
	cmd.PersistentFlags().StringVar(&opencostSvcName, "opencost-service-name", "kubecost-cost-analyzer", "Service name of opencost/kubecost to port-forward")
	cmd.PersistentFlags().IntVar(&opencostSvcPort, "opencost-service-port", 9003, "Service port of opencost/kubecost (use 9090 for in cluster)")

	// required for in-cluster storage data sync
	cmd.PersistentFlags().StringVar(&prometheusNamespace, "prometheus-namespace", "kube-prometheus-stack", "Namespace where main prometheus server is running")
	cmd.PersistentFlags().StringVar(&prometheusSvcName, "prometheus-service-name", "kube-prometheus-stack-prometheus", "Service name of prometheus to port-forward")
	cmd.PersistentFlags().IntVar(&prometheusSvcPort, "prometheus-service-port", 9090, "Service port of prometheus server (use 9090 for in cluster)")

	// required for external storage data sync
	cmd.PersistentFlags().StringVar(&mothershipRegion, "mothership-region", "", "AWS region of mothership")

	// ref. https://docs.kubecost.com/apis/apis-overview/allocation#querying
	cmd.PersistentFlags().StringVar(&queryPath, "query-path", "/allocation/compute", "Query path")
	cmd.PersistentFlags().StringVar(&queryAgg, "query-aggregate", "cluster,namespace,pod", "Query aggregate")
	cmd.PersistentFlags().StringVar(&queryResolution, "query-resolution", "1m", "Query resolution")
	cmd.PersistentFlags().IntVar(&syncInterval, "sync-interval-in-minutes", 10, "Interval to sync data to db")

	cmd.PersistentFlags().BoolVar(&enableStorage, "enable-storage", false, "enables efs storage data sync (default false)")
	cmd.PersistentFlags().BoolVar(&enableCompute, "enable-compute", false, "enables compute data sync, only available in-cluster (default false)")
	cmd.PersistentFlags().BoolVar(&inCluster, "in-cluster", false, "run sync on cluster (default false)")
	cmd.PersistentFlags().StringVar(&clusterName, "cluster-name", "", "name of cluster to run sync on")

	// required to expose metering monitoring and alerting metrics
	cmd.PersistentFlags().IntVar(&listenPort, "listen-port", 31373, "port to serve prometheus metrics on")
	return cmd
}

func syncFunc(cmd *cobra.Command, args []string) {
	if len(clusterName) == 0 {
		log.Fatal("No cluster name provided")
	}
	if 60%syncInterval != 0 {
		log.Fatalf("Invalid sync interval (must be a factor of 60, eg. 5, 10, etc): %d", syncInterval)
	}
	if !(enableStorage || enableCompute) {
		log.Fatalf("Must sync at least one of storage or compute")
	}
	// create aurora db connection
	auroraCfg := common.ReadAuroraConfigFromFlag(cmd)
	db, auroraErr := auroraCfg.NewHandler()
	if auroraErr != nil {
		log.Fatalf("failed to connect to db %v", auroraErr)
	}
	aurora := metering.AuroraDB{DB: db}
	defer aurora.DB.Close()
	log.Printf("Database connection established")

	// set up port forwarding if running externally
	var kubeconfig string
	var restConfig *rest.Config
	var clusterARN string
	var clientset *kubernetes.Clientset
	var fwd *service.PortForwardQuerier
	var err error
	if !inCluster {
		kubeconfig = os.Getenv("KUBECONFIG")
		if kubeconfigPath != "" {
			kubeconfig = kubeconfigPath
		}
		// build rest config
		restConfig, clusterARN, err = common.BuildRestConfig(kubeconfig)
		if err != nil {
			log.Fatalf("failed to build rest config %v", err)
		}

		if strings.Split(clusterARN, "/")[1] != clusterName {
			log.Fatalf("--cluster-name flag %s does not match the cluster name %s specified in the provided KUBECONFIG", clusterName, strings.Split(clusterARN, "/")[1])
		}
		// build k8s clientset
		clientset, err = kubernetes.NewForConfig(restConfig)
		if err != nil {
			log.Fatalf("failed to build k8s clientset %v", err)
		}

		// set timeout for querying pods to get the service information
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		fwd, err = service.NewPortForwardQuerier(
			ctx,
			clientset,
			restConfig,
			opencostNamespace,
			opencostSvcName,
			opencostSvcPort,
		)
		if err != nil {
			log.Fatalf("failed to create port forwarder for service %v", err)
		}
		defer func() {
			cancel()
			fwd.Stop()
		}()
	} else {
		go func() {
			// set up prometheus handler if running in cluster
			metering.RegisterFineGrainHandlers()
			http.HandleFunc("/metrics", promhttp.Handler().ServeHTTP)
			err := http.ListenAndServe(fmt.Sprintf(":%d", listenPort), nil)
			if err != nil {
				log.Fatalf("couldn't start prometheus metrics server: %v", err)
			}
		}()
	}

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
			_, lastComputeSync, err := metering.GetMostRecentFineGrainEntry(aurora, metering.MeteringTableComputeFineGrain, clusterName)
			if err != nil {
				log.Fatalf("failed to get most recent query time %v", err)
			}
			lastComputeSyncExists := !lastComputeSync.IsZero()

			_, lastStorageSync, err := metering.GetMostRecentFineGrainEntry(aurora, metering.MeteringTableStorageFineGrain, clusterName)
			if err != nil {
				log.Fatalf("failed to get most recent query time %v", err)
			}
			lastStorageSyncExists := !lastStorageSync.IsZero()

			now := time.Now()
			currMinute := now.Minute()
			if currMinute%syncInterval == 0 {
				timeSinceLastComputeSync := now.Sub(lastComputeSync)
				timeSinceLastStorageSync := now.Sub(lastStorageSync)
				queryEnd := time.Date(now.Year(), now.Month(), now.Day(), now.Hour(), currMinute, 0, 0, now.Location())
				queryStart := queryEnd.Add(-1 * syncDuration)

				canSyncCompute := false
				canSyncStorage := false
				if enableCompute {
					canSyncCompute = timeSinceLastComputeSync > syncDuration || !lastComputeSyncExists
				}
				if enableStorage {
					canSyncStorage = timeSinceLastStorageSync > syncDuration || !lastStorageSyncExists
				}
				if !(canSyncCompute || canSyncStorage) {
					log.Printf("Cannot sync compute or storage: waiting until next cycle")
				}
				syncOnce(canSyncCompute, canSyncStorage, clusterName, queryStart, queryEnd, aurora, clientset, fwd, cmd)
			} else {
				timeUntilNextSync := now.Truncate(syncDuration).Add(syncDuration).Sub(now)
				// print every minute
				if now.Second() < 10 {
					log.Printf("Next sync in %s", timeUntilNextSync.Round(time.Minute))
				}
			}
		}
	}
}

func syncOnce(syncCompute bool, syncStorage bool, clusterName string, start time.Time, end time.Time, aurora metering.AuroraDB, clientset *kubernetes.Clientset, fwd *service.PortForwardQuerier, cmd *cobra.Command) {
	qp := metering.OcQueryParams{
		OCSvcName:          opencostSvcName,
		OCNamespace:        opencostNamespace,
		OCPort:             opencostSvcPort,
		ClusterName:        clusterName,
		QueryPath:          queryPath,
		QueryAgg:           queryAgg,
		QueryAcc:           false,
		QueryResolution:    queryResolution,
		QueryStart:         start,
		QueryEnd:           end,
		ExcludedNamespaces: metering.ExcludedNamespaces,
	}

	var computeData []metering.FineGrainComputeData
	var err error
	if syncCompute {
		log.Printf("Syncing kubecost compute data with window (%s -- %s)", start, end)
		if inCluster {
			computeData, err = metering.GetFineGrainComputeDataInCluster(qp)
		} else {
			computeData, err = metering.GetFineGrainComputeDataExternal(clientset, fwd, qp)
		}
		if err != nil {
			log.Fatalf("failed to get compute data %v", err)
		}
	}

	var storageData []metering.FineGrainStorageData
	if syncStorage {
		log.Printf("Syncing efs storage data with window query start: (%s -- %s)", start, end)
		if !inCluster {
			storageData, err = metering.GetFineGrainStorageDataExternal(end, mothershipRegion, clusterName)
		} else {
			storageData, err = metering.GetFineGrainStorageDataInCluster(end, clusterName, prometheusSvcName, prometheusNamespace, prometheusSvcPort)
		}

		if err != nil {
			log.Fatalf("failed to get storage data %v", err)
		}
	}
	// create a new connection each time (in case token/connections expire between syncs)
	err = metering.SyncToFineGrain(aurora, clusterName, computeData, storageData)
	if err != nil {
		log.Printf("Data sync failed for window %s, %s: %v", start.Format(time.ANSIC), end.Format(time.ANSIC), err)
	}
}
