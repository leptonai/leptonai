package e2etests

import (
	"fmt"
	"os"
	"strings"
	"testing"
	"time"

	"gopkg.in/yaml.v2"
)

func TestWorkspaceLogin(t *testing.T) {
	cName := newName(t.Name())
	output, err := client.Login(cName)
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	if !strings.Contains(output, "logged in") {
		t.Fatalf("Expected output to be '%s logged in', got '%s'", cName, output)
	}
	time.Sleep(time.Second)
	err = getAndCheckCurrentWorkspace(cName)
	if err != nil {
		t.Fatal(err)
	}
}
func TestWorkspaceLogout(t *testing.T) {
	output, err := client.Logout()
	if err != nil {
		t.Fatal("Logout failed", err, output)
	}
	if output != "Logged out\n" {
		t.Fatalf("Expected output to be 'Logged out', got '%s'", output)
	}

	time.Sleep(time.Second)
	currentWorkspace, err := getCurrentWorkspace()
	if err != nil {
		t.Fatal(err)
	}
	if currentWorkspace != "" {
		t.Fatalf("Expected to find no logged in workspace, got '%s'", currentWorkspace)
	}
}
func TestWorkspaceLoginLogout(t *testing.T) {
	cName := newName(t.Name())
	output, err := client.Login(cName)
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	if !strings.Contains(output, "logged in") {
		t.Fatalf("Expected output to be '%s logged in', got '%s'", cName, output)
	}
	output, err = client.Logout()
	if err != nil {
		t.Fatal("Logout failed", err, output)
	}
	if output != "Logged out\n" {
		t.Fatalf("Expected output to be 'Logged out', got '%s'", output)
	}
	err = getAndCheckCurrentWorkspace("")
	if err != nil {
		t.Fatal(err)
	}
}

func TestWorkspaceLoginToExisting(t *testing.T) {
	cName := newName(t.Name())
	output, err := client.Login(cName)
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	if !strings.Contains(output, "logged in") {
		t.Fatalf("Expected output to contain '%s logged in', got '%s'", cName, output)
	}
	// Logout
	output, err = client.Logout()
	if err != nil {
		t.Fatal("Logout failed", err, output)
	}
	err = getAndCheckCurrentWorkspace("")
	if err != nil {
		t.Fatal(err)
	}
	// Login again
	fullArgs := []string{"workspace", "login", "-n", cName}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatal("Login Failed", err, output)
	}
	if !strings.Contains(output, "logged in") {
		t.Fatalf("Expected output to contain '%s logged in', got '%s'", cName, output)
	}

	err = getAndCheckCurrentWorkspace(cName)
	if err != nil {
		t.Fatal(err)
	}
}

/*
TODO: right now, cliwrapper does not support passing in stdin to Run(). In the
future we should complete this test by testing if one can login with a new URL.
This is currently being covered in python test with dryrun, so we are relatively
OK for now.
func TestWorkspaceLoginNoURL(t *testing.T) {
	prevWorkspace, err := getCurrentWorkspace()
	if err != nil {
		t.Fatal(err)
	}
	cName := newName(t.Name())
	fullArgs := []string{"workspace", "login", "-n", cName, "-t", client.AuthToken}
	output, err := client.Run(fullArgs...)
	if err == nil {
		t.Fatal("Expected error, got none", output)
	}
	if strings.Contains(output, "logged in") {
		t.Fatalf("Expected output to not contain '%s logged in', got '%s'", cName, output)
	}
	err = getAndCheckCurrentWorkspace(prevWorkspace)
	if err != nil {
		t.Fatal(err)
	}
}
*/

func TestWorkspaceLoginNoFlags(t *testing.T) {
	prevWorkspace, err := getCurrentWorkspace()
	if err != nil {
		t.Fatal(err)
	}
	fullArgs := []string{"workspace", "login"}
	output, err := client.Run(fullArgs...)
	if err == nil {
		t.Fatalf("Expected error, got none: %s", output)
	}
	err = getAndCheckCurrentWorkspace(prevWorkspace)
	if err != nil {
		t.Fatal(err)
	}
}

func TestWorkspaceList(t *testing.T) {
	// login to multiple workspaces
	numWorkspaces := 3
	workspaceNames := []string{}
	for i := 0; i < numWorkspaces; i++ {
		// using "cn" to avoid identical truncated names in console output
		cName := newName("cn")
		workspaceNames = append(workspaceNames, cName)
		output, err := client.Login(cName)
		if err != nil {
			t.Fatal("Login failed", err, output)
		}
	}
	fullArgs := []string{"workspace", "list"}
	output, err := client.Run(fullArgs...)
	if err != nil {
		t.Fatal(output, err)
	}
	for _, name := range workspaceNames {
		// console output is truncated if name is too long
		if len(name) > 10 {
			name = name[0:10]
		}
		if !strings.Contains(output, name) {
			t.Fatalf("Expected output to contain '%s'", name)
		}
	}
}

func getCurrentWorkspace() (string, error) {
	_, err := os.Stat(workspaceInfoPath)
	if os.IsNotExist(err) {
		return "", fmt.Errorf("workspace info file does not exist at %s", workspaceInfoPath)
	} else if err != nil {
		return "", err
	}

	workspaceInfoFile, err := os.ReadFile(workspaceInfoPath)
	if err != nil {
		return "", err
	}
	data := make(map[string]interface{})
	err = yaml.Unmarshal(workspaceInfoFile, &data)
	if err != nil {
		return "", err
	}
	if data["current_workspace"] == nil {
		return "", nil
	}
	return data["current_workspace"].(string), nil
}

func getAndCheckCurrentWorkspace(expected string) error {
	currentWorkspace, err := getCurrentWorkspace()
	if err != nil {
		return err
	}
	if currentWorkspace != expected {
		return fmt.Errorf("expected to find workspace '%s', got '%s'", expected, currentWorkspace)
	}
	return nil
}
