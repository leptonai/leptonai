package e2etests

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/url"
	"testing"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"

	"golang.org/x/net/websocket"
)

func TestInstance(t *testing.T) {
	name := "instance-" + randString(5)
	mustCreatePhoton(t, name)
	mustPushPhoton(t, name)
	mustDeployPhoton(t, name)
	mustVerifyDeployment(t, "deploy-", name)

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
		resp, err := c.Get(*remoteURL + "/deployments/" + deploymentID + "/instances/" + is[0].ID + "/log")
		if err != nil {
			t.Fatal(err)
		}

		if resp.StatusCode != http.StatusOK {
			t.Fatalf("Request failed with status code: %d", resp.StatusCode)
		}

		b := make([]byte, 4096)
		n, err := io.Reader(resp.Body).Read(b)
		b = b[:n]
		if err != nil {
			// expected since it's a long running process
			// e.g., "... (Press CTRL+C to quit)"
			if err != io.ErrUnexpectedEOF {
				t.Fatal(err)
			}
		}

		if !bytes.Contains(b, []byte("running on http")) {
			t.Fatalf("unexpected '/log' output: %s", string(b))
		}
	}
}

// get metrics of a deployment
func testInstanceMonitoring(t *testing.T, deploymentID string) func(t *testing.T) {
	return func(t *testing.T) {
		is := mustListInstance(t, deploymentID)
		c := http.Client{}

		tests := []struct {
			metricsKey  string
			expectedStr string
		}{
			{
				// e.g.,
				// [{"metric":{"name":"memory_util"},"values":[[1686056520,"0.116568"]]}]
				metricsKey:  "memoryUtil",
				expectedStr: `{"name":"memory_util"}`,
			},
			{
				// e.g.,
				// [{"metric":{"name":"memory_usage_in_bytes"},"values":[[1686056473.391,"2801664"],...]}]
				metricsKey:  "memoryUsage",
				expectedStr: `{"name":"memory_usage_in_bytes"}`,
			},
			{
				// e.g.,
				// [{"metric":{"name":"memory_total_in_bytes"},"values":[[1686056475.646,"1024000000"],...]}]
				metricsKey:  "memoryTotal",
				expectedStr: `{"name":"memory_total_in_bytes"}`,
			},
			{
				// e.g.,
				//  [{"metric":{"name":"cpu_util"},"values":[[1686056520,"0.0319154177428367"]]}]
				metricsKey:  "CPUUtil",
				expectedStr: `{"name":"cpu_util"}`,
			},
			{
				metricsKey:  "FastAPIQPS",
				expectedStr: ``,
			},
			{
				metricsKey:  "FastAPILatency",
				expectedStr: ``,
			},
			{
				metricsKey:  "FastAPIByPathQPS",
				expectedStr: ``,
			},
			{
				metricsKey:  "FastAPIByPathLatency",
				expectedStr: ``,
			},
			{
				metricsKey:  "GPUMemoryUtil",
				expectedStr: ``,
			},
			{
				metricsKey:  "GPUMemoryUsage",
				expectedStr: ``,
			},
			{
				metricsKey:  "GPUMemoryTotal",
				expectedStr: ``,
			},
			{
				metricsKey:  "GPUUtil",
				expectedStr: ``,
			},
		}

		for _, tt := range tests {
			found := false
			for i := 0; i < 10; i++ {
				r, err := c.Get(*remoteURL + "/deployments/" + deploymentID + "/instances/" + is[0].ID + "/monitoring/" + tt.metricsKey)
				if err != nil {
					t.Fatal(err)
				}
				b, err := readAll(r.Body)
				if err != nil {
					t.Fatal(err)
				}
				if r.StatusCode != http.StatusOK {
					t.Fatalf("%s request failed with status code: %d", tt, r.StatusCode)
				}
				if tt.expectedStr == "" {
					found = true
					break
				}

				if !bytes.Contains(b, []byte(tt.expectedStr)) {
					t.Logf("[%d] '%s' does not contain the expected string '%s'", i, string(b), tt.expectedStr)
					time.Sleep(5 * time.Second)
					continue
				}

				found = true
				break
			}
			if !found {
				t.Logf("'%s' unexpected output (expected %q)", tt.metricsKey, tt.expectedStr)
			}
		}
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

func readAll(rd io.ReadCloser) ([]byte, error) {
	defer rd.Close()
	return io.ReadAll(rd)
}
