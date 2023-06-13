package e2etests

import (
	"net/http"
	"testing"
	"time"
)

func TestIngressUsingDeploymentDocs(t *testing.T) {
	waitForDeploymentToRunningState(mainTestDeploymentID)
	d, err := lepton.Deployment().Get(mainTestDeploymentID)
	if err != nil {
		t.Fatal(err)
	}
	if d.Status.Endpoint.ExternalEndpoint == "" {
		t.Fatal("Expected deployment to have an external endpoint, got empty string")
	}
	waitForDNSPropagation(d.Status.Endpoint.ExternalEndpoint)
	// TODO after net.ResolveIP, net/http still cannot resolve IP of the domain name. Why?
	retryUntilNoErrorOrTimeout(10*time.Minute, func() error {
		out, err := lepton.HTTP.Request(http.MethodGet, "https://"+d.Status.Endpoint.ExternalEndpoint+"/docs", nil, nil)
		if err != nil {
			return err
		}
		if len(out) == 0 {
			t.Fatal("Expected non-empty response, got empty string")
		}
		return nil
	})
}
