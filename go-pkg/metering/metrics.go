package metering

import (
	"context"
	"encoding/json"
	"time"

	"github.com/prometheus/client_golang/api"
	v1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/client_golang/prometheus"
)

type PrometheusStorageQuery struct {
	Metric PrometheusStorageQueryMetrics `json:"metric"`
	Value  []interface{}                 `json:"value"`
}

type PrometheusStorageQueryMetrics struct {
	ClusterName string `json:"cluster_name"`
	WorkspaceID string `json:"workspace_id"`
	SizeInBytes int64  `json:"size_bytes"`
	StorageID   string `json:"storage_id"`
}

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

// Query the prometheus server at promURL with an instance selector for the given queryStr, at specified queryTime
func QueryPrometheus(promURL, queryStr string, queryTime time.Time) ([]byte, error) {
	client, err := api.NewClient(api.Config{Address: promURL})
	if err != nil {
		return nil, err
	}

	v1API := v1.NewAPI(client)
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	result, _, err := v1API.Query(ctx, queryStr, queryTime)
	if err != nil {
		return nil, err
	}

	return json.Marshal(result)
}
