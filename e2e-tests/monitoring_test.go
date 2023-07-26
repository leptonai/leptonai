package e2etests

import (
	"encoding/json"
	"strings"
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
	for _, name := range replicaMonitoringInterfaces {
		replicas, err := lepton.Replica().List(mainTestDeploymentName)
		if err != nil {
			t.Errorf("failed to list replicas: %s", err)
		}
		if len(replicas) < 1 {
			t.Errorf("no replicas found for deployment %s", mainTestDeploymentName)
		}
		replicaID := replicas[0].ID
		raw, err := lepton.Monitoring().GetReplicaRaw(name, mainTestDeploymentName, replicaID)
		if err != nil {
			t.Errorf("failed to get replica raw for name %s and replica %s: %s", name, replicaID, err)
		}
		s := []interface{}{}
		err = json.Unmarshal([]byte(raw), &s)
		if err != nil {
			t.Errorf("failed to unmarshal output for name %s and replica %s: %s, with output: %s", name, replicaID, err, raw)
		}
		if len(s) == 0 {
			// skip GPU monitoring because no GPU is available in CI clusters
			if !strings.HasPrefix(name, "GPU") &&
				// skip FastAPI monitoring because no request was sent so no data is available
				!strings.HasPrefix(name, "FastAPI") {
				t.Errorf("failed to get any data for name %s and replica %s", name, replicaID)
			}
		}
	}
}

func TestDeploymentMonitoring(t *testing.T) {
	for _, name := range deploymentMonitoringInterfaces {
		raw, err := lepton.Monitoring().GetDeploymentRaw(name, mainTestDeploymentName)
		if err != nil {
			t.Errorf("failed to get deployment raw for name %s: %s", name, err)
		}
		s := []interface{}{}
		err = json.Unmarshal([]byte(raw), &s)
		if err != nil {
			t.Errorf("failed to unmarshal output for name %s: %s, with output %s", name, err, raw)
		}
		if len(s) == 0 {
			// skip GPU monitoring because no GPU is available in CI clusters
			if !strings.HasPrefix(name, "GPU") &&
				// skip FastAPI monitoring because no request was sent so no data is available
				!strings.HasPrefix(name, "FastAPI") {
				t.Errorf("failed to get any data for name %s", name)
			}
		}
	}
}
