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
			t.Fatal(err)
		}
		if len(instances) < 1 {
			t.Fatal("no instances found")
		}
		instanceID := instances[0].ID
		raw, err := lepton.Monitoring().GetInstanceRaw(name, mainTestDeploymentID, instanceID)
		if err != nil {
			t.Fatal(err)
		}
		s := []interface{}{}
		err = json.Unmarshal([]byte(raw), &s)
		if err != nil {
			t.Fatal(err)
		}
	}
}

func TestDeploymentMonitoring(t *testing.T) {
	for _, name := range deploymentMonitoringInterfaces {
		raw, err := lepton.Monitoring().GetDeploymentRaw(name, mainTestDeploymentID)
		if err != nil {
			t.Fatal(err)
		}
		s := []interface{}{}
		err = json.Unmarshal([]byte(raw), &s)
		if err != nil {
			t.Fatal(err)
		}
	}
}
