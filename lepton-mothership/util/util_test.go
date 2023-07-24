package util

import (
	"testing"
)

func TestValidateName(t *testing.T) {
	if !ValidateName("test123") {
		t.Error("validateName failed")
	}
	// include dash
	if ValidateName("test-123") {
		t.Error("validateName failed")
	}
	if ValidateName("0atest") {
		t.Error("validateName failed")
	}
	if ValidateName("Test") {
		t.Error("validateName failed")
	}
	if !ValidateName("abcdefghijklmnopqrst") {
		t.Error("validateName failed")
	}
	// too long
	if ValidateName("abcdefghijklmnopqrstu") {
		t.Error("validateName failed")
	}
}
