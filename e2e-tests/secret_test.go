package e2etests

import (
	"sort"
	"testing"

	"github.com/leptonai/lepton/go-pkg/k8s/secret"
)

func TestSecret(t *testing.T) {
	// Test create
	s := []secret.SecretItem{
		{
			Name:  "key1",
			Value: "value1",
		},
		{
			Name:  "key2",
			Value: "value2",
		},
	}
	if err := lepton.Secret().Create(s); err != nil {
		t.Fatal(err)
	}
	// Test list
	secrets, err := lepton.Secret().List()
	if err != nil {
		t.Fatal(err)
	}
	if len(secrets) != 2 {
		t.Fatalf("Expected 2 secrets, got %d", len(secrets))
	}
	sort.Strings(secrets)
	if secrets[0] != "key1" {
		t.Fatalf("Expected key1, got %s", secrets[0])
	}
	if secrets[1] != "key2" {
		t.Fatalf("Expected key2, got %s", secrets[1])
	}
	// Test update
	s = []secret.SecretItem{
		{
			Name:  "key1",
			Value: "value3",
		},
	}
	if err := lepton.Secret().Create(s); err != nil {
		t.Fatal(err)
	}
	secrets, err = lepton.Secret().List()
	if err != nil {
		t.Fatal(err)
	}
	if len(secrets) != 2 {
		t.Fatalf("Expected 2 secrets, got %d", len(secrets))
	}
	// Test add
	s = []secret.SecretItem{
		{
			Name:  "key3",
			Value: "value4",
		},
	}
	if err := lepton.Secret().Create(s); err != nil {
		t.Fatal(err)
	}
	secrets, err = lepton.Secret().List()
	if err != nil {
		t.Fatal(err)
	}
	if len(secrets) != 3 {
		t.Fatalf("Expected 3 secrets, got %d", len(secrets))
	}
	// Test delete
	for _, key := range secrets {
		if err := lepton.Secret().Delete(key); err != nil {
			t.Fatal(err)
		}
	}
	secrets, err = lepton.Secret().List()
	if err != nil {
		t.Fatal(err)
	}
	if len(secrets) != 0 {
		t.Fatalf("Expected 0 secrets, got %d", len(secrets))
	}
}
