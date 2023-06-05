package ingress

import "testing"

func TestPrefixPaths(t *testing.T) {
	p := NewPrefixPaths().
		AddServicePath("test", 80, "/test").
		AddAnnotationPath("test", "/test")
	if len(p.Get()) != 2 {
		t.Error("PrefixPaths failed")
	}
}
