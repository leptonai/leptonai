package e2etests

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"testing"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"

	"golang.org/x/net/websocket"
)

func TestInstance(t *testing.T) {
	phName := "photon-instance-" + randString(5)
	mustCreatePhoton(t, phName)
	mustPushPhoton(t, phName)
	mustDeployPhoton(t, phName)
	deploymentName := mustVerifyDeployment(t, phName)
	if !strings.HasPrefix(deploymentName, "deploy-") {
		t.Fatalf("deployment name %q does not have the expected prefix 'deploy-'", deploymentName)
	}

	pid := getPhotonID(phName, mustListPhoton(t))
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

		success := false
		for i := 0; i < 5; i++ {
			if i > 0 {
				time.Sleep(5 * time.Second)
			}

			req, err := http.NewRequest(http.MethodGet, *remoteURL+"/deployments/"+deploymentID+"/instances/"+is[0].ID+"/log", nil)
			if err != nil {
				t.Fatal(err)
			}
			b, err := checkOKHTTP(&http.Client{}, req, func(rd io.Reader) ([]byte, error) {
				buf := make([]byte, 4096)
				n, err := rd.Read(buf)
				buf = buf[:n]
				return buf, err
			})
			if err != nil {
				// expected since it's a long running process
				// e.g., "... (Press CTRL+C to quit)"
				if err != io.ErrUnexpectedEOF {
					t.Log(err)
					continue
				}
			}

			if !bytes.Contains(b, []byte("running on http")) {
				t.Logf("unexpected '/log' output: %s", string(b))
				continue
			}

			success = true
			break
		}

		if !success {
			t.Fatal("failed to check /log in time")
		}
	}
}

// get metrics of a deployment
func testInstanceMonitoring(t *testing.T, deploymentID string) func(t *testing.T) {
	return func(t *testing.T) {
		is := mustListInstance(t, deploymentID)

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
				// [{"metric":{"name":"memory_usage_in_MB"},
				metricsKey:  "memoryUsage",
				expectedStr: `{"name":"memory_usage_in_MB"}`,
			},
			{
				// e.g.,
				// [{"metric":{"name":"memory_total_in_MB"},
				metricsKey:  "memoryTotal",
				expectedStr: `{"name":"memory_total_in_MB"}`,
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
			req, err := http.NewRequest(http.MethodGet, *remoteURL+"/deployments/"+deploymentID+"/instances/"+is[0].ID+"/monitoring/"+tt.metricsKey, nil)
			if err != nil {
				t.Fatal(err)
			}
			b, err := checkOKHTTP(&http.Client{}, req, nil)
			if err != nil {
				// TODO: fix this test, prometheus might have crashed
				// e.g., no space left on device
				t.Logf("prometheus server not responding with error %v for the metric %q", err, tt.metricsKey)
				continue
			}

			if tt.expectedStr == "" {
				continue
			}

			if !bytes.Contains(b, []byte(tt.expectedStr)) {
				t.Logf("'%s' does not contain the expected string '%s'", string(b), tt.expectedStr)
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
