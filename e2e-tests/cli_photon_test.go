package e2etests

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

var (
	// is there a good way to handle the error?
	homeDir, _        = os.UserHomeDir()
	leptonCacheDir    = filepath.Join(homeDir, ".cache", "lepton")
	workspaceInfoPath = filepath.Join(leptonCacheDir, "workspace_info.yaml")
	cliTestPhotonName = newName("cli-test-photon")
)

func TestCLIPhotonCreateNoName(t *testing.T) {
	fullArgs := []string{"photon", "create", "-m", modelName}
	output, err := client.Run(fullArgs...)
	if err == nil {
		t.Fatal("Expected error since no name was provided, got none", output)
	}
}

func TestCLIPhotonCreateNoModel(t *testing.T) {
	fullArgs := []string{"photon", "create", "-n", newName(cliTestPhotonName)}
	output, err := client.Run(fullArgs...)
	if err == nil {
		t.Fatal("Expected error since no model was provided, got none", output)
	}
}

func TestCLIPhotonCreatePushWithLogin(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	pName := newName(cliTestPhotonName)
	output, err = createAndCheckPhoton(pName, modelName)
	if err != nil {
		t.Fatalf("Failed to check photon %s with err '%s' and output '%s'", pName, err, output)
	}
	fullArgs := []string{"photon", "push", "-n", pName}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatal(err)
	}
	expected := "Photon " + pName + " pushed to workspace."
	if !strings.Contains(output, expected) {
		t.Fatalf("Expected output to be '%s', got '%s'", expected, output)
	}

	time.Sleep(time.Second)
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
	output, err = client.Logout()
	if err != nil {
		t.Fatalf("Logout failed with err '%s' and output '%s'", err, output)
	}
}

func TestCLIPhotonPushWithoutLogin(t *testing.T) {
	output, err := client.Logout()
	if err != nil {
		t.Fatal("Logout failed", err, output)
	}
	pName := newName(cliTestPhotonName)
	output, err = createAndCheckPhoton(pName, modelName)
	if err != nil {
		t.Fatalf("Failed to check photon %s with err '%s' and output '%s'", pName, err, output)
	}
	fullArgs := []string{"photon", "push", "-n", pName}
	output, err = client.Run(fullArgs...)
	if err == nil {
		t.Fatal("Expected error since not logged in, got none", err, output)
	}
}

func TestCLIPhotonPushNonexistent(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	dummyName := newName("dummy")
	fullArgs := []string{"photon", "push", "-n", dummyName}
	output, err = client.Run(fullArgs...)
	if err == nil {
		t.Fatal("Expected error since a dummyName was provided, got none", output)
	}
}

func TestCLIPhotonRunLoggedIn(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	pName := newName(cliTestPhotonName)
	output, err = createAndCheckPhoton(pName, modelName)
	if err != nil {
		t.Fatalf("Failed to check photon %s with err '%s' and output '%s'", pName, err, output)
	}
	fullArgs := []string{"photon", "push", "-n", pName}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatal("photon push failed:", err, output)
	}
	time.Sleep(time.Second)
	phs, err := lepton.Photon().GetByName(pName)
	if err != nil {
		log.Fatal(err)
	}
	if len(phs) != 1 {
		log.Fatal("Expected 1 photon, got ", len(phs))
	}
	ph := phs[0]
	pid := ph.ID

	fullArgs = []string{"photon", "run", "-n", pName, "--resource-shape", "gp1.hidden_test"}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatal(err, output)
	}
	fullArgs = []string{"photon", "run", "-i", pid, "--resource-shape", "gp1.hidden_test"}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatal(err, output)
	}
	time.Sleep(time.Second)
	ds, err := lepton.Deployment().List()
	if err != nil {
		log.Fatal(err)
	}
	if len(ds) < 2 {
		t.Fatalf("Expected at least 2 deployment, got %d", len(ds))
	}
	// cleanup
	for _, d := range ds {
		if d.PhotonID == pid {
			err = lepton.Deployment().Delete(d.Name)
			if err != nil {
				log.Fatal(err)
			}
		}
	}
}

func TestCLIPhotonList(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login Failed", err, output)
	}
	numPhotons := 3
	pNames := []string{}
	for i := 0; i < numPhotons; i++ {
		// using lt to prevent truncated names from being identical
		pName := newName("lt")
		pNames = append(pNames, pName)
		fullArgs := []string{"photon", "create", "-n", pName, "-m", modelName}
		output, err = client.Run(fullArgs...)
		if err != nil {
			t.Fatalf("Create photon %s failed: %s %s", pName, err, output)
		}
		fullArgs = []string{"photon", "push", "-n", pName}
		output, err = client.Run(fullArgs...)
		if err != nil {
			t.Fatalf("Push photon %s fialed: %s %s", pName, err, output)
		}
	}

	fullArgs := []string{"photon", "list"}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatal("Photon list failed", err, output)
	}
	for _, pName := range pNames {
		// console output will truncate photon names if too long
		if len(pName) > 15 {
			pName = pName[:15]
		}
		if !strings.Contains(output, pName) {
			t.Fatalf("Expected output to contain %s, got %s", pName, output)
		}
	}
}

func createAndCheckPhoton(name string, model string) (string, error) {
	fullArgs := []string{"photon", "create", "-n", name, "-m", model}
	output, err := client.Run(fullArgs...)
	if err != nil {
		return output, err
	}
	expected := "Photon " + name + " created"
	if !strings.Contains(output, expected) {
		return output, fmt.Errorf("Expected output to be '%s', got '%s'", expected, output)
	}
	return output, nil
}
