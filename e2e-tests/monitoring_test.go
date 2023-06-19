package e2etests

import (
	"encoding/json"
	"testing"
)

var (
	instanceMonitoringInterfaces = []string{
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

func TestInstanceMonitoring(t *testing.T) {
	for _, name := range instanceMonitoringInterfaces {
		instances, err := lepton.Instance().List(mainTestDeploymentID)
		if err != nil {
			t.Fatalf("failed to list instances: %s", err)
		}
		if len(instances) < 1 {
			t.Fatalf("no instances found for deployment %s", mainTestDeploymentID)
		}
		instanceID := instances[0].ID
		raw, err := lepton.Monitoring().GetInstanceRaw(name, mainTestDeploymentID, instanceID)
		if err != nil {
			t.Fatalf("failed to get instance raw for name %s and instance %s: %s", name, instanceID, err)
		}
		s := []interface{}{}
		err = json.Unmarshal([]byte(raw), &s)
		if err != nil {
			t.Fatalf("failed to unmarshal output for name %s and instance %s: %s, with output: %s", name, instanceID, err, raw)
		}
	}
}

func TestDeploymentMonitoring(t *testing.T) {
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
