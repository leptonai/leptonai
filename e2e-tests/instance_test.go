package e2etests

import (
	"encoding/json"
	"net/http"
	"testing"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
)

func TestInstance(t *testing.T) {
	name := "instance-" + randString(5)
	mustCreatePhoton(t, name)
	mustPushPhoton(t, name)
	mustDeployPhoton(t, name)
	mustVerifyDeployment(t, name)

	pid := getPhotonID(name, mustListPhoton(t))
	did := mustGetDeploymentIDbyPhotonID(t, pid)

	t.Run("list", testInstanceList(t, did))
	t.Run("log", testInstanceLog(t, did))
	t.Run("metrics", testInstanceMetrics(t, did))
}

func testInstanceList(t *testing.T, deploymentID string) func(t *testing.T) {
	return func(t *testing.T) {
		is := mustListInstance(t, deploymentID)
		if len(is) != 1 {
			t.Fatal("failed to list instances")
		}
	}
}

func testInstanceLog(t *testing.T, deploymentID string) func(t *testing.T) {
	return func(t *testing.T) {
		is := mustListInstance(t, deploymentID)
		c := http.Client{}
		r, err := c.Get(*remoteURL + "/deployments/" + deploymentID + "/instances/" + is[0].ID + "/log")
		if err != nil {
			t.Fatal(err)
		}
		defer r.Body.Close()

		if r.StatusCode != http.StatusOK {
			t.Fatalf("Request failed with status code: %d", r.StatusCode)
		}
		// TODO: check log content
	}
}

func testInstanceMetrics(t *testing.T, deploymentID string) func(t *testing.T) {
	return func(t *testing.T) {
		is := mustListInstance(t, deploymentID)
		c := http.Client{}

		tests := []string{"memoryUtil", "memoryUsage", "memoryTotal", "CPUUtil",
			"FastAPIQPS", "FastAPILatency", "FastAPIByPathQPS", "FastAPIByPathLatency",
			"GPUMemoryUtil", "GPUMemoryUsage", "GPUMemoryTotal", "GPUUtil"}

		for _, tt := range tests {
			r, err := c.Get(*remoteURL + "/deployments/" + deploymentID + "/instances/" + is[0].ID + "/monitoring/" + tt)
			if err != nil {
				t.Fatal(err)
			}

			if r.StatusCode != http.StatusOK {
				t.Fatalf("Request failed with status code: %d", r.StatusCode)
			}
			r.Body.Close()
		}

		// TODO: check metrics content
	}
}

func mustListInstance(t *testing.T, deploymentID string) []httpapi.Instance {
	c := http.Client{}
	r, err := c.Get(*remoteURL + "/deployments/" + deploymentID + "/instances")
	if err != nil {
		t.Fatal(err)
	}
	defer r.Body.Close()

	if r.StatusCode != http.StatusOK {
		t.Fatalf("Request failed with status code: %d", r.StatusCode)
	}

	var is []httpapi.Instance
	err = json.NewDecoder(r.Body).Decode(&is)
	if err != nil {
		t.Fatal(err)
	}

	return is
}
