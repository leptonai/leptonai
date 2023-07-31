// Package metrics defines lepton common metrics.
package metrics

import (
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
)

var (
	httpReqsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "http",
			Subsystem: "requests",
			Name:      "total",
			Help:      "Tracks all HTTP requests",
		},
		[]string{"component", "api", "method", "status_code"},
	)
	httpReqsLatency = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Namespace: "http",
			Subsystem: "requests",
			Name:      "latency_seconds",

			// lowest bucket start of upper bound 0.001 sec (1 ms) with factor 2
			// highest bucket start of 8.192 sec = 0.001 * pow(2, 13).
			Buckets: prometheus.ExponentialBuckets(0.001, 2, 14),
		},
		[]string{"component", "api", "method", "status_code"},
	)
)

func init() {
	prometheus.MustRegister(
		httpReqsTotal,
		httpReqsLatency,
	)
}

// PrometheusMiddlewareForGin is a Gin middleware that exports Prometheus metrics.
func PrometheusMiddlewareForGin(component string) gin.HandlerFunc {
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

		httpReqsTotal.WithLabelValues(component, api, method, statusCode).Inc()
		httpReqsLatency.WithLabelValues(component, api, method, statusCode).Observe(took.Seconds())
	}
}
