package util

import (
	"testing"
)

func TestValidateName(t *testing.T) {
	// cluster and workspace shared test cases
	tests := []struct {
		name  string
		valid bool
	}{
		{"test123", true},
		{"0atest", false},
		{"Test", false},
		{"abcdefghijklmnopqrst", true},
		// too long
		{"abcdefghijklmnopqrstu", false},
	}

	for _, test := range tests {
		if ValidateClusterName(test.name) != test.valid {
			t.Error("validateName failed for cluster name: " + test.name)
		}

		if ValidateWorkspaceName(test.name) != test.valid {
			t.Error("validateName failed for workspace name: " + test.name)
		}
	}

	// dashes are only allowed for cluster id not for workspace id
	if !ValidateClusterName("test-123") {
		t.Error("validateName failed")
	}

	if ValidateWorkspaceName("test-123") {
		t.Error("validateName failed")
	}
}