package e2etests

import (
	"fmt"
	"os/exec"
	"testing"
)

func TestDeploymentCreate(t *testing.T) {
	name := "deploy-" + randString(5)

	mustCreatePhoton(t, name)
	mustPushPhoton(t, name)

	mustDeployPhoton(t, name)

	// TODO: verify the Kubernetes deployment is up and running
}

func mustDeployPhoton(t *testing.T, name string) {
	id := getPhotonID(name, mustListPhoton(t))

	cmd := exec.Command("lepton", "photon", "run", "-i", id, "-r", *remoteULR)
	out, err := cmd.Output()
	if err != nil {
		fmt.Println(string(out))
		t.Fatal(err)
	}
}
