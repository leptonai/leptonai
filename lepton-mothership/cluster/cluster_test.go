package cluster

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
)

func TestPrometheus_getTotalClusters(t *testing.T) {
	reg := prometheus.NewRegistry()
	reg.MustRegister(clusterTotal)

	clusterTotal.Inc()
	r := getTotalClusters(reg)
	if r != 1.0 {
		t.Fatalf("expected 1.0, got %d", r)
	}
}
