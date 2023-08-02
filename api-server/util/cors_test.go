package util

import (
	"net/http"
	"testing"
)

func TestCORSForDashboard(t *testing.T) {
	h := http.Header{}

	SetCORSForDashboard(h, "")

	err := CheckCORSForDashboard(h, "")
	if err != nil {
		t.Fatal(err)
	}

	UnsetCORSForDashboard(h)
	err = CheckCORSForDashboard(h, "")
	if err == nil {
		t.Fatal("CORS header should be unset")
	}

	if len(h) != 0 {
		t.Fatal("CORS header should be empty")
	}
}

func TestCORSForDashboardWithCustomDomain(t *testing.T) {
	domain := "https://example.com"
	h := http.Header{}

	SetCORSForDashboard(h, domain)

	err := CheckCORSForDashboard(h, domain)
	if err != nil {
		t.Fatal(err)
	}

	UnsetCORSForDashboard(h)
	err = CheckCORSForDashboard(h, domain)
	if err == nil {
		t.Fatal("CORS header should be unset")
	}

	if len(h) != 0 {
		t.Fatal("CORS header should be empty")
	}
}
