package e2etests

import (
	"net/http"
	"net/url"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
)

func TestIngressWithDeploymentDocsUsingHeaderBased(t *testing.T) {
	waitForDeploymentToRunningState(mainTestDeploymentID)
	endpoint, err := url.Parse(*workspaceURL)
	if err != nil {
		t.Fatalf("Expected workspace URL to be a valid URL, got %s", *workspaceURL)
	}
	url := endpoint.Scheme + "://" + endpoint.Hostname() + ":" + endpoint.Port() + "/docs"
	header := map[string]string{
		ingress.HTTPHeaderNameForDeployment: mainTestDeploymentID,
	}
	err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		out, err := lepton.HTTP.RequestURL(http.MethodGet, url, header, nil)
		if err != nil {
			return err
		}
		if len(out) == 0 {
			t.Fatal("Expected non-empty response, got empty string")
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestIngressWithDeploymentDocsUsingHostBased(t *testing.T) {
	waitForDeploymentToRunningState(mainTestDeploymentID)
	d, err := lepton.Deployment().Get(mainTestDeploymentID)
	if err != nil {
		t.Fatal(err)
	}
	if d.Status.Endpoint.ExternalEndpoint == "" {
		t.Fatal("Expected deployment to have an external endpoint, got empty string")
	}
	endpoint := d.Status.Endpoint.ExternalEndpoint
	url, err := url.Parse(endpoint)
	if err != nil {
		t.Fatal("Expected the external endpoint to be a valid URL, got ", endpoint)
	}
	if err := waitForDNSPropagation(url.Hostname()); err != nil {
		t.Fatalf("Expected DNS to propagate for %s, got %v", url.Hostname(), err)
	}
	// TODO after net.ResolveIP, net/http still cannot resolve IP of the domain name. Why?
	err = retryUntilNoErrorOrTimeout(time.Minute, func() error {
		out, err := lepton.HTTP.RequestURL(http.MethodGet, endpoint+"/docs", nil, nil)
		if err != nil {
			return err
		}
		if len(out) == 0 {
			t.Fatal("Expected non-empty response, got empty string")
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}
