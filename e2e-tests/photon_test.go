package e2etests

import (
	"log"
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

		out, err := client.RunLocal("photon", "create", "-n", pName, "-m", "hf:gpt2")
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
	out, err := client.RunLocal("photon", "create", "-n", pName, "-m", "hf:gpt2")
	if err != nil {
		log.Fatalf("Failed to create photon %s: %s: %s", pName, err, out)
	}
	out, err = client.RunRemote("photon", "push", "-n", pName)
	if err != nil {
		log.Fatalf("Failed to push photon %s: %s: %s", pName, err, out)
	}
	out, err = client.RunRemote("photon", "push", "-n", pName)
	if err == nil {
		log.Fatalf("Expected error when pushing photon %s twice, got none: %s", pName, out)
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
