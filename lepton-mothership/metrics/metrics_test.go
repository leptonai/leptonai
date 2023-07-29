package metrics

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
)

func TestGetTotalClusters(t *testing.T) {
	reg := prometheus.NewRegistry()
	reg.MustRegister(clustersTotal)

	clustersTotal.Inc()
	r := GetTotalClusters(reg)
	if r != 1.0 {
		t.Fatalf("expected 1.0, got %d", r)
	}
}
