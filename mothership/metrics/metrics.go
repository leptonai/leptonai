// Package metrics implements a Prometheus metrics exporter for the lepton-mothership.
package metrics

import (
	"context"
	"log"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
)

var (
	clustersTotal = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Namespace: "mothership",
			Subsystem: "clusters",
			Name:      "total",
			Help:      "Tracks the total number of clusters",
		},
	)
	clusterJobsSuccessTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "mothership",
			Subsystem: "cluster_jobs",
			Name:      "success_total",
			Help:      "Tracks successful mothership cluster job operations (asynchronous calls)",
		},
		[]string{"job"},
	)
	clusterJobsFailureTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "mothership",
			Subsystem: "cluster_jobs",
			Name:      "failure_total",
			Help:      "Tracks failed mothership cluster job operations (asynchronous calls)",
		},
		[]string{"job"},
	)
	clusterJobsLatency = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Namespace: "mothership",
			Subsystem: "cluster_jobs",
			Name:      "latency_seconds",

			// lowest bucket start of upper bound 60 sec (1 min) with factor 2
			// highest bucket start of 2-hour (7200 seconds)
			Buckets: prometheus.ExponentialBuckets(60, 2, 12),
		},
		[]string{"job", "success"},
	)
)

type jobKind string

const jobKindCtxKey = jobKind("job-kind")

// NewCtxWithJobKind returns a new context with the job kind key.
func NewCtxWithJobKind(jk string) context.Context {
	return context.WithValue(context.Background(), jobKindCtxKey, jk)
}

// ReadJobKindFromCtx returns the job kind string value from the context.
func ReadJobKindFromCtx(ctx context.Context) string {
	return ctx.Value(jobKindCtxKey).(string)
}

func init() {
	prometheus.MustRegister(
		clustersTotal,
		clusterJobsSuccessTotal,
		clusterJobsFailureTotal,
		clusterJobsLatency,
	)
}

// GetTotalClusters returns the total number of clusters from the default Prometheus gatherer.
func GetTotalClusters(gatherer prometheus.Gatherer) int {
	gss, err := gatherer.Gather()
	if err != nil {
		log.Printf("failed to get default gatherer %v", err)
		return 0
	}
	for _, gs := range gss {
		if gs.GetName() == "mothership_clusters_total" && len(gs.Metric) > 0 {
			return int(*gs.Metric[0].GetGauge().Value)
		}
	}
	return 0
}

// IncrementClusterJobsSuccessTotal increments the total number of clusters.
func IncrementClustersTotal() {
	clustersTotal.Inc()
}

// DecrementClusterJobsSuccessTotal decrements the total number of clusters.
func DecrementClustersTotal() {
	clustersTotal.Dec()
}

// IncrementClusterJobsSuccessTotal increments the total number of successful cluster jobs.
func IncrementClusterJobsSuccessTotal(job string) {
	clusterJobsSuccessTotal.WithLabelValues(job).Inc()
}

// IncrementClusterJobsFailureTotal increments the total number of failed cluster jobs.
func IncrementClusterJobsFailureTotal(job string) {
	clusterJobsFailureTotal.WithLabelValues(job).Inc()
}

// ObserveClusterJobsLatency tracks the latency of cluster jobs.
func ObserveClusterJobsLatency(job string, success bool, took time.Duration) {
	clusterJobsLatency.WithLabelValues(job, strconv.FormatBool(success)).Observe(took.Seconds())
}
