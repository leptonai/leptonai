package e2etests

import (
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
	name := "push-" + randString(5)
	mustCreatePhoton(t, name)
	mustPushPhoton(t, name)

	id := getPhotonID(name, mustListPhoton(t))
	if id == "" {
		t.Fatal("Cannot find the ID of the push Photon:", id)
	}
}

func TestPhotonRemove(t *testing.T) {
	name := "remove-" + randString(5)

	mustCreatePhoton(t, name)
	mustPushPhoton(t, name)

	id := getPhotonID(name, mustListPhoton(t))
	if id == "" {
		t.Fatal("Cannot find the ID of the push Photon:", id)
	}

	mustRemovePhoton(t, name, id)
}

func mustListPhoton(t *testing.T) string {
	cmd := exec.Command("lepton", "photon", "list", "-r", *remoteURL)
	out, err := cmd.Output()
	if err != nil {
		fmt.Println(string(out))
		t.Fatal(err)
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
}

func mustPushPhoton(t *testing.T, name string) {
	cmd := exec.Command("lepton", "photon", "push", "-n", name, "-r", *remoteURL)
	output, err := cmd.Output()
	if err != nil {
		fmt.Println(string(output))
		t.Fatal(err)
	}
}

func mustRemovePhoton(t *testing.T, name, id string) {
	cmd := exec.Command("lepton", "photon", "remove", "-i", id, "-r", *remoteURL)
	output, err := cmd.Output()
	if err != nil {
		fmt.Println(string(output))
		t.Fatal(err)
	}
	did := getPhotonID(name, string(output))
	if id == did {
		t.Fatal("Failed to remove the Photon:", did)
	}
}

func randString(length int) string {
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[seededRand.Intn(len(charset))]
	}
	return string(b)
}
