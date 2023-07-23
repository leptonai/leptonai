package e2etests

import (
	"strings"
	"testing"
)

func TestCLISecretCreateListRemove(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	dummyName := newName("DUMMY_SECRET")
	dummyValue := newName("DUMMY_SECRET_VALUE")
	illegalName := newName("LEPTON_SECRET_1")

	fullCreateArgs := []string{"secret", "create", "-n", dummyName, "-v", dummyValue}
	output, err = client.Run(fullCreateArgs...)
	if err != nil {
		t.Fatal("Creating secret failed.", output)
	}
	if !strings.Contains(output, dummyName) {
		t.Fatalf("Expected output to contain %s, got %s", dummyName, output)
	}

	fullCreateIllegalNameArgs := []string{"secret", "create", "-n", illegalName, "-v", dummyValue}
	output, err = client.Run(fullCreateIllegalNameArgs...)
	if err == nil {
		t.Fatalf("Expected error since secret %s is an illegal name, got %s", illegalName, output)
	}

	fullListArgs := []string{"secret", "list"}
	output, err = client.Run(fullListArgs...)
	if err != nil {
		t.Fatal("Creating secret failed.", output)
	}
	if !strings.Contains(output, dummyName) {
		t.Fatalf("Expected output to contain %s, got %s", dummyName, output)
	}
	if strings.Contains(output, dummyValue) {
		t.Fatalf("Expected output to not contain secret value %s, got %s", dummyValue, output)
	}

	fullRemoveArgs := []string{"secret", "remove", "-n", dummyName}
	output, err = client.Run(fullRemoveArgs...)
	if err != nil {
		t.Fatal("Removing secret failed.", output)
	}
	if !strings.Contains(output, dummyName) {
		t.Fatalf("Expected output to contain %s, got %s", dummyName, output)
	}

	fullListAgainArgs := []string{"secret", "list"}
	output, err = client.Run(fullListAgainArgs...)
	if err != nil {
		t.Fatal("Creating secret failed.", output)
	}
	if strings.Contains(output, dummyName) {
		t.Fatalf("Expected output to not contain %s, got %s", dummyName, output)
	}
}
