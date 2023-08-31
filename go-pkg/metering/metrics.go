package metering

import (
	"github.com/prometheus/client_golang/prometheus"
)

var (
	// metering metrics are exposed by metering-sync and metering-aggregate
	// used to monitor metering deployment health and data streaming to databases
	meteringCounter = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "lepton",
			Subsystem: "metering",
			Name:      "update_operations_total",
		},
		[]string{
			// which cluster is the data from?
			"cluster_name",
			// 'compute_fine_grain', 'storage_hourly', etc
			"table_name",
			// either 'aurora' or 'supabase'
			"db_type",
		},
	)
	meteringAmount = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: "lepton",
			Subsystem: "metering",
			Name:      "last_sync_updated_rows",
		},
		[]string{"cluster_name", "table_name", "db_type"},
	)

	meteringLDAmountFineGrain = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: "lepton",
			Subsystem: "metering",
			Name:      "last_sync_lepton_deployments",
		},
		[]string{"cluster_name"},
	)

	// storage metrics, exposed via the lepton api server
	// used to gather storage usage data for billing purposes
	storageDiskUsageBytes = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: "lepton",
			Subsystem: "storage",
			Name:      "workspace_usage_bytes",
		},
		[]string{
			// which workspace is the data from?
			"workspace_id",
			//  which cluster is the data from?
			"cluster_name",
			// i.e 'efs'
			"type",
			// apiserver/httpapi/main.go's *efsIdFlag, for example
			"storage_id",
		},
	)
)

func RegisterAggregateHandlers() {
	prometheus.MustRegister(
		meteringCounter,
		meteringAmount,
	)
}

func RegisterFineGrainHandlers() {
	prometheus.MustRegister(
		meteringCounter,
		meteringAmount,
		meteringLDAmountFineGrain,
	)
}

func RegisterStorageHandlers() {
	prometheus.MustRegister(
		storageDiskUsageBytes,
	)
}

// GatherAggregate exports Prometheus metrics for metering-related aggregate operations
func GatherAggregate(clusterName string, tableName string, dbHost string, latestAmount float64) {
	meteringCounter.WithLabelValues(clusterName, tableName, dbHost).Inc()
	meteringAmount.WithLabelValues(clusterName, tableName, dbHost).Set(latestAmount)
}

// GatherFineGrain exports Prometheus metrics for metering-related fine-grain operations
func GatherFineGrain(clusterName string, tableName string, latestAmount float64, latestLDAmount float64) {
	meteringCounter.WithLabelValues(clusterName, tableName, "aurora").Inc()
	meteringAmount.WithLabelValues(clusterName, tableName, "aurora").Set(latestAmount)

	if tableName == string(MeteringTableComputeFineGrain) {
		meteringLDAmountFineGrain.WithLabelValues(clusterName).Set(latestLDAmount)
	}
}

// GatherDiskUsage exports Prometheus metrics for workspace disk usage
func GatherDiskUsage(workspaceId string, clusterName string, storageType string, storageId string, diskUsageBytes int64) {
	storageDiskUsageBytes.WithLabelValues(workspaceId, clusterName, storageType, storageId).Set(float64(diskUsageBytes))
}
