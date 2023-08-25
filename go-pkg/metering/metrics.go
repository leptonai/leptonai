package metering

import (
	"github.com/prometheus/client_golang/prometheus"
)

var (
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
