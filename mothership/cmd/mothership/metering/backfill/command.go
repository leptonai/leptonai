package backfill

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/go-pkg/metering"
	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"

	"github.com/araddon/dateparse"
	"github.com/spf13/cobra"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

var (
	kubeconfigPath string

	opencostNamespace string
	opencostSvcName   string
	opencostSvcPort   int

	queryPath       string
	queryAgg        string
	queryResolution string

	backfillIntervalFlag int
	startFlag            string
	endFlag              string
	durationFlag         time.Duration
	previewBackfill      bool

	inCluster   bool
	clusterName string
)

func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "backfill",
		Short: "Backfill metering data from kubecost/opencost to fine grain db",
		Long: `
Backfill a cluster's metering data from kubecost/opencost to fine_grained table.
By default, this starts from the most recent fine_grained sync, up to the current time.
Optionally, you can specify a start and end time to backfill.
Furthermore, if the duration flag is specified, the start time will be ignored, and the backfill will proceed from end-time - duration

Specifying the --preview-dry flag will display all gaps in the fine_grain data from the provided start to end time, and all exact
query windows that will be executed. No database writes will occur.


Usage:
- Use kubeconfig stored at KUBECONFIG env var, and backfill in 10 minute intervals starting from July 1st, 2023:
$ mothership metering backfill --start '07/01/2023 00:00:00+00' --backfill-interval-minutes 10

- Use kubeconfig stored at /tmp/dev-kubeconfig, and backfill in 10 minute intervals (default interval) starting from July 1st, 3:30 PM UTC, 2023 to July 1st, 4:00 PM UTC, 2023:
$ mothership metering backfill -k '/tmp/dev-kubeconfig' --start-backfill '07/01/2023 15:00:00+00' --end-backfill '07/01/2023 16:00:00+00'

- Preview the 10 minute query intervals for a backfill of data, fromthe  most recent fine_grain sync time to current time:
$ mothership metering backfill --preview-dry

- Auto-backfill all gaps from 07/11/2023 midnight UTC to 07/14/2023 midnight UTC (counting from the first query after 7/11 midnight)
$ mothership metering backfill --start '07/11/2023 00:00:00+00' --end '07/14/2023 00:00:00+00'
`,
		Run: backfillFunc,
	}
	cmd.PersistentFlags().StringVarP(&kubeconfigPath, "kubeconfig", "k", "", "Kubeconfig path (otherwise, client uses the one from KUBECONFIG env var)")
	cmd.PersistentFlags().StringVarP(&opencostNamespace, "opencost-namespace", "n", "kubecost-cost-analyzer", "Namespace where opencost/kubecost is running")
	cmd.PersistentFlags().StringVarP(&opencostSvcName, "opencost-service-name", "s", "kubecost-cost-analyzer", "Service name of opencost/kubecost to port-forward")
	cmd.PersistentFlags().IntVarP(&opencostSvcPort, "opencost-service-port", "t", 9003, "Service port of opencost/kubecost (use 9090 for in cluster)")

	// ref. https://docs.kubecost.com/apis/apis-overview/allocation#querying
	cmd.PersistentFlags().StringVar(&queryPath, "query-path", "/allocation/compute", "Query path")
	cmd.PersistentFlags().StringVar(&queryAgg, "query-aggregate", "cluster,namespace,pod", "Query aggregate")
	cmd.PersistentFlags().StringVar(&queryResolution, "query-resolution", "1m", "Query resolution")

	cmd.PersistentFlags().IntVarP(&backfillIntervalFlag, "backfill-interval-minutes", "i", 10, "Interval to sync data to db, in minutes")
	cmd.PersistentFlags().StringVar(&startFlag, "start-time", "", "Start time for backfill, defaults to most recent query")
	cmd.PersistentFlags().StringVar(&endFlag, "end-time", "", "End time for backfill, defaults to current time")
	cmd.PersistentFlags().DurationVar(&durationFlag, "duration", 0, "Duration of backfill (overrides start flag)")

	cmd.PersistentFlags().BoolVar(&previewBackfill, "preview-dry", false, "display all intervals to be backfilled for the current operation. Does not run any database queries.")
	cmd.PersistentFlags().BoolVar(&inCluster, "in-cluster", false, "run backfill from an in-cluster deployment")
	cmd.PersistentFlags().StringVar(&clusterName, "cluster-name", "", "name of cluster to run backfill on")
	return cmd
}

func backfillFunc(cmd *cobra.Command, args []string) {
	if len(clusterName) == 0 {
		log.Fatal("No cluster name provided")
	}

	// connect to aurora
	auroraCfg := common.ReadAuroraConfigFromFlag(cmd)
	db, err := auroraCfg.NewHandler()
	if err != nil {
		log.Fatalf("Failed to connect to db: %v", err)
	}
	auroraDB := metering.AuroraDB{DB: db}
	defer auroraDB.DB.Close()

	if 60%backfillIntervalFlag != 0 {
		log.Fatalf("Invalid sync interval %d, must evenly divide 60 (e.g 5, 10, 15)", backfillIntervalFlag)
	}
	backfillInterval := time.Duration(backfillIntervalFlag) * time.Minute

	var backfillStart, backfillEnd time.Time
	if endFlag != "" {
		backfillEnd, err = dateparse.ParseAny(endFlag)
		if err != nil {
			log.Fatalf("Failed to parse end time: %v", err)
		}
	} else {
		backfillEnd = time.Now().UTC().Truncate(backfillInterval)
	}
	// duration flag takes precedence over start flag
	if durationFlag != 0 {
		backfillStart = backfillEnd.Add(-durationFlag)
	} else if startFlag != "" {
		backfillStart, err = dateparse.ParseAny(startFlag)
		if err != nil {
			log.Fatalf("Failed to parse start time: %v", err)
		}
	} else {
		_, backfillStart, err = metering.GetMostRecentFineGrainEntry(auroraDB, metering.MeteringTableComputeFineGrain, clusterName)
		if err != nil {
			log.Fatalf("Failed to get latest sync time: %v", err)
		}
		if backfillStart.IsZero() {
			log.Fatal("No previous sync found, please specify a start time")
		}
	}
	// truncate to the nearest sync interval
	backfillStart = backfillStart.Truncate(backfillInterval)
	backfillEnd = backfillEnd.Truncate(backfillInterval)

	//sanity checks
	if backfillEnd.Before(backfillStart) || backfillEnd.Equal(backfillStart) {
		log.Fatalf("shifted backfill end time %s is before or equal to query start time %s",
			backfillEnd.Format(time.RFC3339), backfillStart.Format(time.RFC3339))
	}
	if backfillEnd.Sub(backfillStart) < backfillInterval {
		log.Fatalf("shifted backfill window %s is shorter than sync interval %d min",
			backfillEnd.Sub(backfillStart).String(), backfillInterval)
	}
	log.Printf("Backfill (%s, %s)", backfillStart.Format(time.RFC3339), backfillEnd.Format(time.RFC3339))

	// set up portforwarding if run externally
	var kubeconfig string
	var restConfig *rest.Config
	var clusterARN string
	var clientset *kubernetes.Clientset
	var fwd *service.PortForwardQuerier
	if !inCluster {
		kubeconfig = os.Getenv("KUBECONFIG")
		if kubeconfigPath != "" {
			kubeconfig = kubeconfigPath
		}
		restConfig, clusterARN, err = common.BuildRestConfig(kubeconfig)
		if err != nil {
			log.Fatalf("Failed to build rest config: %v", err)
		}
		if strings.Split(clusterARN, "/")[1] != clusterName {
			log.Fatalf("--cluster-name flag %s does not match the cluster name %s specified in the provided KUBECONFIG", clusterName, strings.Split(clusterARN, "/")[1])
		}
		clientset, err = kubernetes.NewForConfig(restConfig)
		if err != nil {
			log.Fatalf("Failed to build clientset: %v", err)
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
			log.Fatalf("Failed to build port forwarder: %v", err)
		}
		defer func() {
			cancel()
			fwd.Stop()
		}()
	}

	var gaps [][]time.Time
	retryErr := util.Retry(5, 2*time.Second, func() (err error) {
		gaps, err = metering.GetGapsInFineGrain(auroraDB, clusterName, backfillStart, backfillEnd)
		return
	})
	if retryErr != nil {
		log.Fatalf("Failed to find gaps: %v", err)
	}

	var startTimes, endTimes []time.Time
	for _, gap := range gaps {
		startTimesForGap, endTimesForGap := getBackfillQueryIntervals(gap[0], gap[1], backfillInterval)
		startTimes = append(startTimes, startTimesForGap...)
		endTimes = append(endTimes, endTimesForGap...)
	}

	if previewBackfill {
		fmt.Printf("----GAPS IN DATA----\n")
		for _, gap := range gaps {
			fmt.Printf("%s ---- %s\n", gap[0].Format(time.RFC3339), gap[1].Format(time.RFC3339))
		}
		fmt.Printf("--------------------\n")
		fmt.Printf("----QUERY INTERVALS----\n")
		for i := 0; i < len(startTimes); i++ {
			fmt.Printf("%s ---- %s\n", startTimes[i].Format(time.RFC3339), endTimes[i].Format(time.RFC3339))
		}
		fmt.Printf("-----------------------\n")
		return
	}

	for i := 0; i < len(startTimes); i++ {
		log.Printf("Backfilling from %v to %v", startTimes[i], endTimes[i])
		qp := metering.OcQueryParams{
			OCSvcName:          opencostSvcName,
			OCNamespace:        opencostNamespace,
			OCPort:             opencostSvcPort,
			ClusterName:        clusterName,
			QueryPath:          queryPath,
			QueryAgg:           queryAgg,
			QueryAcc:           false,
			QueryResolution:    queryResolution,
			QueryStart:         startTimes[i],
			QueryEnd:           endTimes[i],
			ExcludedNamespaces: metering.ExcludedNamespaces,
		}
		// TODO: use Kubecost Allocation API's `step` query param to return multiple intervals in one query
		var computeData []metering.FineGrainComputeData
		retryGetErr := util.Retry(5, 2*time.Second, func() (err error) {
			if inCluster {
				computeData, err = metering.GetFineGrainComputeDataInCluster(qp)
			} else {
				computeData, err = metering.GetFineGrainComputeDataExternal(clientset, fwd, qp)
			}
			if err != nil {
				log.Printf("Failed to get compute data, retrying: %v", err)
				return err
			}
			return nil
		})
		if retryGetErr != nil {
			log.Printf("Failed to get data query with window %s - %s: %v", startTimes[i], endTimes[i], retryErr)
		}
		retryInsertErr := util.Retry(5, 2*time.Second, func() (err error) {
			// no storage data to backfill, so we pass nil
			err = metering.SyncToFineGrain(auroraDB, computeData, nil)
			if err != nil {
				log.Printf("Failed to insert data, retrying: %v", err)
				return err
			}
			return nil
		})
		if retryInsertErr != nil {
			log.Printf("Failed to insert data query with window %s - %s: %v", startTimes[i], endTimes[i], retryErr)
		}
	}
	log.Printf("Backfill complete")
}

func getBackfillQueryIntervals(backfillStart, backfillEnd time.Time, backfillInterval time.Duration) ([]time.Time, []time.Time) {
	// generate backfill querying intervals
	var startTimes []time.Time
	var endTimes []time.Time
	if backfillEnd.Sub(backfillStart) < backfillInterval {
		startTimes = append(startTimes, backfillStart)
		endTimes = append(endTimes, backfillEnd)
		return startTimes, endTimes
	}
	for t := backfillStart; t.Before(backfillEnd); t = t.Add(backfillInterval) {
		startTimes = append(startTimes, t)
		endTimes = append(endTimes, t.Add(backfillInterval))
	}
	if len(startTimes) != len(endTimes) {
		log.Fatalf("%d start times generated but %d end times generated", len(startTimes), len(endTimes))
	}
	return startTimes, endTimes
}
