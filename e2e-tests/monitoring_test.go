package e2etests

import (
	"encoding/json"
	"testing"
)

var (
	replicaMonitoringInterfaces = []string{
		"memoryUtil",
		"memoryUsage",
		"memoryTotal",
		"CPUUtil",
		"FastAPIQPS",
		"FastAPILatency",
		"FastAPIByPathQPS",
		"FastAPIByPathLatency",
		"GPUMemoryUtil",
		"GPUMemoryUsage",
		"GPUMemoryTotal",
		"GPUUtil",
	}
	deploymentMonitoringInterfaces = []string{
		"FastAPIQPS",
		"FastAPILatency",
		"FastAPIQPSByPath",
		"FastAPILatencyByPath",
	}
)

func TestReplicaMonitoring(t *testing.T) {
	t.Skip("Skipping Prometheus related tests until we merge https://github.com/leptonai/lepton/pull/1410")
	for _, name := range replicaMonitoringInterfaces {
		replicas, err := lepton.Replica().List(mainTestDeploymentID)
		if err != nil {
			t.Fatalf("failed to list replicas: %s", err)
		}
		if len(replicas) < 1 {
			t.Fatalf("no replicas found for deployment %s", mainTestDeploymentID)
		}
		replicaID := replicas[0].ID
		raw, err := lepton.Monitoring().GetReplicaRaw(name, mainTestDeploymentID, replicaID)
		if err != nil {
			t.Fatalf("failed to get replica raw for name %s and replica %s: %s", name, replicaID, err)
		}
		s := []interface{}{}
		err = json.Unmarshal([]byte(raw), &s)
		if err != nil {
			t.Fatalf("failed to unmarshal output for name %s and replica %s: %s, with output: %s", name, replicaID, err, raw)
		}
	}
}

func TestDeploymentMonitoring(t *testing.T) {
	t.Skip("Skipping Prometheus related tests until we merge https://github.com/leptonai/lepton/pull/1410")
	for _, name := range deploymentMonitoringInterfaces {
		raw, err := lepton.Monitoring().GetDeploymentRaw(name, mainTestDeploymentID)
		if err != nil {
			t.Fatalf("failed to get deployment raw for name %s: %s", name, err)
		}
		s := []interface{}{}
		err = json.Unmarshal([]byte(raw), &s)
		if err != nil {
			t.Fatalf("failed to unmarshal output for name %s: %s, with output %s", name, err, raw)
		}
	}
}
