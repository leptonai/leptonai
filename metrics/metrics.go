// Package metrics defines lepton common metrics.
package metrics

import (
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/prometheus/client_golang/prometheus"
)

var (
	httpReqsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "lepton",
			Subsystem: "http_requests",
			Name:      "total",
			Help:      "Tracks all HTTP requests",
		},
		[]string{"component", "api", "method", "status_code"},
	)
	httpReqsLatency = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Namespace: "lepton",
			Subsystem: "http_requests",
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

		api, componentsN := deriveAPIPrefix(c.FullPath())
		if componentsN < 3 { // do not log special endpoints
			return
		}

		method := c.Request.Method
		statusCode := strconv.Itoa(c.Writer.Status())

		httpReqsTotal.WithLabelValues(component, api, method, statusCode).Inc()
		httpReqsLatency.WithLabelValues(component, api, method, statusCode).Observe(took.Seconds())
	}
}

// Returns the up to the first 3 elements of the path.
// And the number of the elements.
//
// e.g.,
// "c.FullPath" returns "/user/:id"
// always use the first element "user"
// only use the first 3 elements as we prefix with api groups
// /api/v1/...
func deriveAPIPrefix(fullPath string) (string, int) {
	splits := util.RemoveEmptyStringFromSlice(strings.Split(fullPath, "/"))
	n := len(splits)
	if n > 3 {
		splits = splits[:3]
		n = 3
	}
	return "/" + strings.Join(splits, "/"), n
}
