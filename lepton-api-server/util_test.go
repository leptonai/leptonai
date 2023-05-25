package main

import "testing"

func TestValidateName(t *testing.T) {
	if !validateName("test") {
		t.Error("validateName failed")
	}
	if !validateName("test-123") {
		t.Error("validateName failed")
	}
	if !validateName("test-123-abc") {
		t.Error("validateName failed")
	}
	if !validateName("test--test") {
		t.Error("validateName failed")
	}
	if validateName("-test") {
		t.Error("validateName failed")
	}
	if validateName("0a-test") {
		t.Error("validateName failed")
	}
	if validateName("Test") {
		t.Error("validateName failed")
	}
	if validateName("test-") {
		t.Error("validateName failed")
	}
	if validateName("test-123-abc-xyz-") {
		t.Error("validateName failed")
	}
	if !validateName("abcdef0123456789") {
		t.Error("validateName failed")
	}
	if validateName("abcdef01234567899") {
		t.Error("validateName failed")
	}
}
