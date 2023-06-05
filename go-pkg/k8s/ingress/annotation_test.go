package ingress

import "testing"

func TestAnnotation(t *testing.T) {
	NewAnnotation("domain", "cert").
		SetDomainNameAndSSLCert().
		SetGroup("group", 100).
		Add("key", "value")
	// TODO: add more tests
}
