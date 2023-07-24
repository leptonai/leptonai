package ingress

import "testing"

func TestAnnotation(t *testing.T) {
	NewAnnotation("domain", "cert").
		SetDomainNameAndSSLCert().
		SetGroup("group", 100).
		Add("key", "value")
	// TODO: add more tests
}

func TestAddBearerToTokens(t *testing.T) {
	input := []string{}
	output := addBearerToTokens(input)
	if len(output) != 0 {
		t.Errorf("Expected empty slice, got %v", output)
	}

	input = []string{"token1"}
	output = addBearerToTokens(input)
	if len(output) != 1 {
		t.Errorf("Expected 1 token, got %v", output)
	}
	if output[0] != "Bearer token1" {
		t.Errorf("Expected Bearer token1, got %v", output[0])
	}

	input = []string{"token1", "token2"}
	output = addBearerToTokens(input)
	if len(output) != 2 {
		t.Errorf("Expected 2 tokens, got %v", output)
	}
	if output[0] != "Bearer token1" {
		t.Errorf("Expected Bearer token1, got %v", output[0])
	}
	if output[1] != "Bearer token2" {
		t.Errorf("Expected Bearer token2, got %v", output[1])
	}
}