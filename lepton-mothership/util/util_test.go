package util

import (
	"testing"
)

func TestValidateName(t *testing.T) {
	if !ValidateName("test123") {
		t.Error("validateName failed")
	}
	if ValidateName("test-123") {
		t.Error("validateName failed")
	}
	if ValidateName("0atest") {
		t.Error("validateName failed")
	}
	if ValidateName("Test") {
		t.Error("validateName failed")
	}
	if !ValidateName("abcdefghijklmnop") {
		t.Error("validateName failed")
	}
	if ValidateName("abcdefghijklmnopq") {
		t.Error("validateName failed")
	}
}
