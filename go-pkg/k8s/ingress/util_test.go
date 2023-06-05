package ingress

import "testing"

func TestIngressName(t *testing.T) {
	if IngressName("test") != "test-ingress" {
		t.Error("IngressName failed")
	}
}

func TestIngressNameForHeaderBased(t *testing.T) {
	if IngressNameForHeaderBased("test") != "test-header-ingress" {
		t.Error("IngressNameForHeaderBased failed")
	}
}

func TestIngressNameForHostBased(t *testing.T) {
	if IngressNameForHostBased("test") != "test-host-ingress" {
		t.Error("IngressNameForHostBased failed")
	}
}

func TestIngressGroupNameDeployment(t *testing.T) {
	if IngressGroupNameDeployment("test") != "lepton-test-control-plane" {
		t.Error("IngressGroupNameDeployment failed")
	}
}

func TestIngressGroupNameControlPlane(t *testing.T) {
	if IngressGroupNameControlPlane("test") != "lepton-test-control-plane" {
		t.Error("IngressGroupNameControlPlane failed")
	}
}
