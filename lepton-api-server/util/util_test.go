package util

import "testing"

func TestValidateName(t *testing.T) {
	if !ValidateName("test") {
		t.Error("validateName failed")
	}
	if !ValidateName("test-123") {
		t.Error("validateName failed")
	}
	if !ValidateName("test-123-abc") {
		t.Error("validateName failed")
	}
	if !ValidateName("test--test") {
		t.Error("validateName failed")
	}
	if ValidateName("-test") {
		t.Error("validateName failed")
	}
	if ValidateName("0a-test") {
		t.Error("validateName failed")
	}
	if ValidateName("Test") {
		t.Error("validateName failed")
	}
	if ValidateName("test-") {
		t.Error("validateName failed")
	}
	if ValidateName("test-123-abc-xyz-") {
		t.Error("validateName failed")
	}
	if !ValidateName("abcdef0123456789") {
		t.Error("validateName failed")
	}
	if ValidateName("abcdef01234567899") {
		t.Error("validateName failed")
	}
}
