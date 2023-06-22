package e2etests

import (
	"fmt"
	"os"
	"strings"
	"testing"
	"time"

	"gopkg.in/yaml.v2"
)

func TestRemoteLogin(t *testing.T) {
	cName := newName(t.Name())
	output, err := client.Login(cName)
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	if !strings.Contains(output, "logged in") {
		t.Fatalf("Expected output to be '%s logged in', got '%s'", cName, output)
	}
	time.Sleep(time.Second)
	err = getAndCheckCurrentCluster(cName)
	if err != nil {
		t.Fatal(err)
	}
}
func TestRemoteLogout(t *testing.T) {
	output, err := client.Logout()
	if err != nil {
		t.Fatal("Logout failed", err, output)
	}
	if output != "Logged out\n" {
		t.Fatalf("Expected output to be 'Logged out', got '%s'", output)
	}

	time.Sleep(time.Second)
	currentCluster, err := getCurrentCluster()
	if err != nil {
		t.Fatal(err)
	}
	if currentCluster != "" {
		t.Fatalf("Expected to find no logged in cluster, got '%s'", currentCluster)
	}
}
func TestRemoteLoginLogout(t *testing.T) {
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
	err = getAndCheckCurrentCluster("")
	if err != nil {
		t.Fatal(err)
	}
}

func TestRemoteLoginToExisting(t *testing.T) {
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
	err = getAndCheckCurrentCluster("")
	if err != nil {
		t.Fatal(err)
	}
	// Login again
	fullArgs := []string{"remote", "login", "-n", cName}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatal("Login Failed", err, output)
	}
	if !strings.Contains(output, "logged in") {
		t.Fatalf("Expected output to contain '%s logged in', got '%s'", cName, output)
	}

	err = getAndCheckCurrentCluster(cName)
	if err != nil {
		t.Fatal(err)
	}
}

func TestRemoteLoginNoURL(t *testing.T) {
	prevCluster, err := getCurrentCluster()
	if err != nil {
		t.Fatal(err)
	}
	cName := newName(t.Name())
	fullArgs := []string{"remote", "login", "-n", cName, "-t", client.AuthToken}
	output, err := client.Run(fullArgs...)
	if err == nil {
		t.Fatal("Expected error, got none", output)
	}
	if strings.Contains(output, "logged in") {
		t.Fatalf("Expected output to not contain '%s logged in', got '%s'", cName, output)
	}
	err = getAndCheckCurrentCluster(prevCluster)
	if err != nil {
		t.Fatal(err)
	}
}

func TestRemoteLoginNoFlags(t *testing.T) {
	prevCluster, err := getCurrentCluster()
	if err != nil {
		t.Fatal(err)
	}
	fullArgs := []string{"remote", "login"}
	output, err := client.Run(fullArgs...)
	if err == nil {
		t.Fatalf("Expected error, got none: %s", output)
	}
	err = getAndCheckCurrentCluster(prevCluster)
	if err != nil {
		t.Fatal(err)
	}
}

func TestRemoteList(t *testing.T) {
	// login to multiple clusters
	numClusters := 3
	clusterNames := []string{}
	for i := 0; i < numClusters; i++ {
		// using "cn" to avoid identical truncated names in console output
		cName := newName("cn")
		clusterNames = append(clusterNames, cName)
		output, err := client.Login(cName)
		if err != nil {
			t.Fatal("Login failed", err, output)
		}
	}
	fullArgs := []string{"remote", "list"}
	output, err := client.Run(fullArgs...)
	if err != nil {
		t.Fatal(output, err)
	}
	for _, name := range clusterNames {
		// console output is truncated if name is too long
		if len(name) > 10 {
			name = name[0:10]
		}
		if !strings.Contains(output, name) {
			t.Fatalf("Expected output to contain '%s'", name)
		}
	}
}

func getCurrentCluster() (string, error) {
	_, err := os.Stat(clusterInfoPath)
	if os.IsNotExist(err) {
		return "", fmt.Errorf("cluster info file does not exist at %s", clusterInfoPath)
	} else if err != nil {
		return "", err
	}

	clusterInfoFile, err := os.ReadFile(clusterInfoPath)
	if err != nil {
		return "", err
	}
	data := make(map[string]interface{})
	err = yaml.Unmarshal(clusterInfoFile, &data)
	if err != nil {
		return "", err
	}
	if data["current_cluster"] == nil {
		return "", nil
	}
	return data["current_cluster"].(string), nil
}

func getAndCheckCurrentCluster(expected string) error {
	currentCluster, err := getCurrentCluster()
	if err != nil {
		return err
	}
	if currentCluster != expected {
		return fmt.Errorf("expected to find cluster '%s', got '%s'", expected, currentCluster)
	}
	return nil
}
