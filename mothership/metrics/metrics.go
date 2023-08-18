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
			// highest bucket start of 7680 seconds = 60 * pow(2, 7).
			Buckets: prometheus.ExponentialBuckets(60, 2, 8),
		},
		[]string{"job", "success"},
	)
	clusterLogsResponseCount = prometheus.NewCounter(
		prometheus.CounterOpts{
			Namespace: "mothership",
			Subsystem: "cluster_logs",
			Name:      "response_count",
			Help:      "Tracks the response count of cluster logs",
		},
	)
	clusterLogsResponseSum = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Namespace: "mothership",
			Subsystem: "cluster_logs",
			Name:      "response_sum",
			Help:      "Tracks the total response size of cluster logs",
		},
	)

	workspacesTotal = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Namespace: "mothership",
			Subsystem: "workspaces",
			Name:      "total",
			Help:      "Tracks the total number of workspaces",
		},
	)
	workspaceJobsSuccessTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "mothership",
			Subsystem: "workspace_jobs",
			Name:      "success_total",
			Help:      "Tracks successful mothership workspace job operations (asynchronous calls)",
		},
		[]string{"job"},
	)
	workspaceJobsFailureTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "mothership",
			Subsystem: "workspace_jobs",
			Name:      "failure_total",
			Help:      "Tracks failed mothership workspace job operations (asynchronous calls)",
		},
		[]string{"job"},
	)
	workspaceJobsLatency = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Namespace: "mothership",
			Subsystem: "workspace_jobs",
			Name:      "latency_seconds",

			// lowest bucket start of upper bound 20 sec with factor 2
			// highest bucket start of 1280 seconds = 20 * pow(2, 6).
			Buckets: prometheus.ExponentialBuckets(20, 2, 7),
		},
		[]string{"job", "success"},
	)
	workspaceLogsResponseCount = prometheus.NewCounter(
		prometheus.CounterOpts{
			Namespace: "mothership",
			Subsystem: "workspace_logs",
			Name:      "response_count",
			Help:      "Tracks the response count of workspace logs",
		},
	)
	workspaceLogsResponseSum = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Namespace: "mothership",
			Subsystem: "workspace_logs",
			Name:      "response_sum",
			Help:      "Tracks the total response size of workspace logs",
		},
	)
)

func init() {
	prometheus.MustRegister(
		clustersTotal,
		clusterJobsSuccessTotal,
		clusterJobsFailureTotal,
		clusterJobsLatency,
		clusterLogsResponseCount,
		clusterLogsResponseSum,

		workspacesTotal,
		workspaceJobsSuccessTotal,
		workspaceJobsFailureTotal,
		workspaceJobsLatency,
		workspaceLogsResponseCount,
		workspaceLogsResponseSum,
	)
}

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

// SetClustersTotal sets the total number of clusters.
func SetClustersTotal(n float64) {
	clustersTotal.Set(n)
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

func TrackClusterLogsResponse(size float64) {
	clusterLogsResponseCount.Inc()
	clusterLogsResponseSum.Add(size)
}

// GetTotalWorkspaces returns the total number of workspaces from the default Prometheus gatherer.
func GetTotalWorkspaces(gatherer prometheus.Gatherer) int {
	gss, err := gatherer.Gather()
	if err != nil {
		log.Printf("failed to get default gatherer %v", err)
		return 0
	}
	for _, gs := range gss {
		if gs.GetName() == "mothership_workspaces_total" && len(gs.Metric) > 0 {
			return int(*gs.Metric[0].GetGauge().Value)
		}
	}
	return 0
}

// SetWorkspacesTotal updates the total number of workspaces.
func SetWorkspacesTotal(n float64) {
	workspacesTotal.Set(n)
}

// IncrementWorkspaceJobsSuccessTotal increments the total number of successful workspace jobs.
func IncrementWorkspaceJobsSuccessTotal(job string) {
	workspaceJobsSuccessTotal.WithLabelValues(job).Inc()
}

// IncrementWorkspaceJobsFailureTotal increments the total number of failed workspace jobs.
func IncrementWorkspaceJobsFailureTotal(job string) {
	workspaceJobsFailureTotal.WithLabelValues(job).Inc()
}

// ObserveWorkspaceJobsLatency tracks the latency of workspace jobs.
func ObserveWorkspaceJobsLatency(job string, success bool, took time.Duration) {
	workspaceJobsLatency.WithLabelValues(job, strconv.FormatBool(success)).Observe(took.Seconds())
}

func TrackWorkspaceLogsResponse(size float64) {
	workspaceLogsResponseCount.Inc()
	workspaceLogsResponseSum.Add(size)
}
