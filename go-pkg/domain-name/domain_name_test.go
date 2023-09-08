package domainname

import (
	"testing"
)

func TestDomainNameEmptyWorkspace(t *testing.T) {
	domainName := New("", "example.com")
	if domainName.GetAPIServer() != "" {
		t.Errorf("Empty namespace domain name should be empty")
	}
	if domainName.GetDeployment("foo") != "" {
		t.Errorf("Empty namespace deployment domain name should be empty")
	}
}
func TestDomainNameEmptyRoot(t *testing.T) {
	domainName := New("workspace", "")
	if domainName.GetAPIServer() != "" {
		t.Errorf("Empty namespace domain name should be empty")
	}
	if domainName.GetDeployment("foo") != "" {
		t.Errorf("Empty namespace deployment domain name should be empty")
	}
}

func TestDomainName(t *testing.T) {
	DomainName := New("foo", "example.com")
	if DomainName.GetAPIServer() != "foo.example.com" {
		t.Errorf("Custom namespace domain name should be foo.example.com")
	}
	if DomainName.GetDeployment("bar") != "foo-bar.example.com" {
		t.Errorf("Custom namespace deployment domain name should be foo-bar.example.com")
	}
}
