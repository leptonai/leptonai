package e2etests

import (
	"encoding/json"
	"log"
	"net/http"
	"net/url"
	"testing"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"

	"golang.org/x/net/websocket"
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
	t.Run("monitoring", testInstanceMonitoring(t, did))
	t.Run("shell", testInstanceShell(t, did))
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

func testInstanceMonitoring(t *testing.T, deploymentID string) func(t *testing.T) {
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
				t.Fatalf("%s request failed with status code: %d", tt, r.StatusCode)
			}
			r.Body.Close()
		}

		// TODO: check metrics content
	}
}

func testInstanceShell(t *testing.T, deploymentID string) func(t *testing.T) {
	return func(t *testing.T) {
		is := mustListInstance(t, deploymentID)
		shellURL := *remoteURL + "/deployments/" + deploymentID + "/instances/" + is[0].ID + "/shell"
		mustTestShell(t, shellURL)
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

func mustTestShell(t *testing.T, shellURL string) {
	u, err := url.Parse(shellURL)
	if err != nil {
		t.Fatal(err)
	}

	prefix := "ws://"
	if u.Scheme == "https" {
		prefix = "wss://"
	}
	url := prefix + u.Host + u.RequestURI()
	origin := u.Scheme + "://" + u.Host

	ws, err := websocket.Dial(url, "", origin)
	if err != nil {
		t.Fatal(err)
	}
	defer ws.Close()

	if _, err := ws.Write(append([]byte{0}, []byte("ls\n")...)); err != nil {
		log.Fatal(err)
	}
	var msg = make([]byte, 512)
	if _, err = ws.Read(msg); err != nil {
		t.Fatal(err)
	}
}
