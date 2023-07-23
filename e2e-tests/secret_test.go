package e2etests

import (
	"sort"
	"testing"

	"github.com/leptonai/lepton/go-pkg/k8s/secret"
)

func TestSecret(t *testing.T) {
	// Test list
	secrets, err := lepton.Secret().List()
	if err != nil {
		t.Fatal(err)
	}
	// Recording the initial number of secrets. The reason is that we reuse the same workspace
	// for all the tests, so we need to make sure that we take into account any secrets that
	// might have been created by other tests.
	initial_len := len(secrets)
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
	secrets, err = lepton.Secret().List()
	if err != nil {
		t.Fatal(err)
	}
	if len(secrets)-initial_len != 2 {
		t.Fatalf("Expected 2 secrets added, got %d", len(secrets)-initial_len)
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
	if len(secrets)-initial_len != 2 {
		t.Fatalf("Expected 2 secrets added, got %d", len(secrets)-initial_len)
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
	if len(secrets)-initial_len != 3 {
		t.Fatalf("Expected 3 secrets added, got %d", len(secrets)-initial_len)
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

func TestInvalidSecretName(t *testing.T) {
	s := []secret.SecretItem{
		{
			Name:  "key1",
			Value: "value1",
		},
		{
			Name:  "lepton_key2",
			Value: "value2",
		},
	}
	if err := lepton.Secret().Create(s); err == nil {
		t.Fatal("Expected error, got nil")
	}
}
