package e2etests

import (
	"bytes"
	"flag"
	"fmt"
	"math/rand"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"
)

const charset = "abcdefghijklmnopqrstuvwxyz"

var (
	seededRand = rand.New(rand.NewSource(time.Now().UnixNano()))
	remoteURL  = flag.String("remote-url", "", "Remote URL for the Lepton API server")
	namespace  = flag.String("namespace", "default", "Kubernetes Namespace for the Lepton API server")
)

func TestMain(m *testing.M) {
	flag.Parse()
	os.Exit(m.Run())
}

func TestPhotonPushAndList(t *testing.T) {
	phName := "photon-push-" + randString(5)
	mustCreatePhoton(t, phName)
	mustPushPhoton(t, phName)

	phID := getPhotonID(phName, mustListPhoton(t))
	if phID == "" {
		t.Fatal("Cannot find the ID of the push Photon:", phID)
	}
}

func TestPhotonRemove(t *testing.T) {
	phName := "photon-remove-" + randString(5)

	mustCreatePhoton(t, phName)
	mustPushPhoton(t, phName)

	phID := getPhotonID(phName, mustListPhoton(t))
	if phID == "" {
		t.Fatal("Cannot find the ID of the push Photon:", phID)
	}

	mustRemovePhoton(t, phName, phID)
}

func mustListPhoton(t *testing.T) string {
	cmd := exec.Command("lepton", "photon", "list", "-r", *remoteURL)
	out, err := cmd.Output()
	if err != nil {
		fmt.Println(string(out))
		t.Fatal(err)
	}

	// just simple string check
	if !bytes.Contains(out, []byte("Photons")) {
		t.Fatalf("unexpected 'photon list' output: %s", string(out))
	}
	return string(out)
}

func getPhotonID(name, output string) string {
	rows := strings.Split(output, "\n")

	for _, row := range rows {
		if strings.Contains(row, name) {
			fields := strings.Split(row, "│")
			if len(fields) >= 4 {
				return strings.TrimSpace(fields[3])
			}
		}
	}
	return ""
}

func mustCreatePhoton(t *testing.T, name string) {
	cmd := exec.Command("lepton", "photon", "create", "-n", name, "-m", "hf:gpt2")
	output, err := cmd.Output()
	if err != nil {
		fmt.Println(string(output))
		t.Fatal(err)
	}
	if !bytes.Contains(output, []byte("created")) {
		t.Fatalf("unexpected 'photon create' output: %s", string(output))
	}
}

func mustPushPhoton(t *testing.T, name string) {
	cmd := exec.Command("lepton", "photon", "push", "-n", name, "-r", *remoteURL)
	output, err := cmd.Output()
	if err != nil {
		fmt.Println(string(output))
		t.Fatal(err)
	}
	if !bytes.Contains(output, []byte(*remoteURL)) {
		t.Fatalf("unexpected 'photon push' output: %s", string(output))
	}
	if !bytes.Contains(output, []byte("pushed")) {
		t.Fatalf("unexpected 'photon push' output: %s", string(output))
	}
}

func mustRemovePhoton(t *testing.T, name, id string) {
	// e.g.,
	// Remote photon "r5e3ujfm" removed
	cmd := exec.Command("lepton", "photon", "remove", "-i", id, "-r", *remoteURL)
	output, err := cmd.Output()
	if err != nil {
		fmt.Println(string(output))
		t.Fatal(err)
	}
	if !bytes.Contains(output, []byte("removed")) {
		t.Fatalf("unexpected 'photon remove' output: %s", string(output))
	}

	cmd = exec.Command("lepton", "photon", "list", "-r", *remoteURL)
	listOutput, err := cmd.Output()
	if err != nil {
		fmt.Println(string(listOutput))
		t.Fatal(err)
	}

	did := getPhotonID(name, string(listOutput))
	if did != "" {
		t.Fatalf("unexpected removed photon id found %q\n(output: %s)", did, string(listOutput))
	}
}

func randString(length int) string {
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[seededRand.Intn(len(charset))]
	}
	return string(b)
}
