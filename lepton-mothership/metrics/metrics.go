// Package metrics implements a Prometheus metrics exporter for the lepton-mothership.
package metrics

import (
	"context"
	"log"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
)

var (
	httpReqsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "mothership",
			Subsystem: "http_requests",
			Name:      "total",
			Help:      "Tracks all mothership HTTP requests",
		},
		[]string{"api", "method", "status_code"},
	)
	httpReqsLatency = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Namespace: "mothership",
			Subsystem: "http_requests",
			Name:      "latency_seconds",

			// lowest bucket start of upper bound 0.001 sec (1 ms) with factor 2
			// highest bucket start of 0.001 sec * 2^13 == 8.192 sec
			Buckets: prometheus.ExponentialBuckets(0.001, 2, 14),
		},
		[]string{"api", "method", "status_code"},
	)
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
		httpReqsTotal,
		httpReqsLatency,
		clustersTotal,
		clusterJobsSuccessTotal,
		clusterJobsFailureTotal,
		clusterJobsLatency,
	)
}

// PrometheusMiddleware is a Gin middleware that exports Prometheus metrics.
func PrometheusMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		c.Next()

		took := time.Since(start)

		// e.g.,
		// "c.FullPath" returns "/user/:id"
		// always use the first element "user"
		// only use the first 3 elements as we prefix with api groups
		// /api/v1/...
		splits := strings.Split(c.FullPath(), "/")
		api := "/" + splits[0]
		if len(splits) > 2 {
			api = "/" + strings.Join(splits[:3], "/")
		}
		method := c.Request.Method
		statusCode := strconv.Itoa(c.Writer.Status())

		httpReqsTotal.WithLabelValues(api, method, statusCode).Inc()
		httpReqsLatency.WithLabelValues(api, method, statusCode).Observe(took.Seconds())
	}
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
