package e2etests

import (
	"log"
	"strings"
	"testing"
	"time"
)

func TestPhotonCreateAndRemove(t *testing.T) {
	numTests := 3
	pNames := []string{}
	// Create photons
	for i := 0; i < numTests; i++ {
		pName := newName(t.Name())
		pNames = append(pNames, pName)

		out, err := client.RunLocal("photon", "create", "-n", pName, "-m", modelName)
		if err != nil {
			log.Fatalf("Failed to create photon %s: %s: %s", pName, err, out)
		}
		out, err = client.RunRemote("photon", "push", "-n", pName)
		if err != nil {
			log.Fatalf("Failed to push photon %s: %s: %s", pName, err, out)
		}
	}
	// Sleep for a bit to let the server reconcile
	time.Sleep(time.Second)
	// Check that photons exist
	phs, err := lepton.Photon().List()
	if err != nil {
		log.Fatal(err)
	}
	if len(phs) < numTests {
		log.Fatal("Expected at least ", numTests, " photons, got ", len(phs))
	}
	// Delete photons
	for _, name := range pNames {
		phs, err = lepton.Photon().GetByName(name)
		if err != nil {
			log.Fatal(err)
		}
		if len(phs) != 1 {
			log.Fatal("Expected 1 photon, got ", len(phs))
		}
		ph := phs[0]
		err = lepton.Photon().Delete(ph.ID)
		if err != nil {
			log.Fatal(err)
		}
	}
}

func TestPhotonPushTwice(t *testing.T) {
	pName := newName(t.Name())
	out, err := client.RunLocal("photon", "create", "-n", pName, "-m", modelName)
	if err != nil {
		log.Fatalf("Failed to create photon %s: %s: %s", pName, err, out)
	}
	out, err = client.RunRemote("photon", "push", "-n", pName)
	if err != nil {
		log.Fatalf("Failed to push photon %s: %s: %s", pName, err, out)
	}
	out, err = client.RunRemote("photon", "push", "-n", pName)

	// re-pushing a photon from CLI returns 0 by default
	if err != nil {
		log.Fatalf("Pushing a photon(%s) twice should not return error code in CLI, got err: %s, out: %s", pName, err, out)
	}

	if !strings.Contains(out, "409 ResourceConflict") {
		log.Fatalf("Expected 409 message when pushing photon %s twice, got: %s", pName, err)
	}
	phs, err := lepton.Photon().GetByName(pName)
	if err != nil {
		log.Fatal(err)
	}
	if len(phs) != 1 {
		log.Fatal("Expected 1 photon, got ", len(phs))
	}
	ph := phs[0]
	err = lepton.Photon().Delete(ph.ID)
	if err != nil {
		log.Fatal(err)
	}
}
