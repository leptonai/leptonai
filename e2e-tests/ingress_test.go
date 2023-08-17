package e2etests

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"testing"
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
)

func TestIngressWithDeploymentDocsUsingHeaderBased(t *testing.T) {
	t.Parallel()
	if !*testDataPlaneRouting {
		t.Skip("Dataplane routing not ready")
	}
	err := waitForDeploymentToRunningState(mainTestDeploymentName)
	if err != nil {
		t.Fatalf("Expected deployment %s to be in running state, got %v", mainTestDeploymentName, err)
	}
	endpoint, err := url.Parse(*workspaceURL)
	if err != nil {
		t.Fatalf("Expected workspace URL to be a valid URL, got %s", *workspaceURL)
	}
	u := endpoint.Scheme + "://" + endpoint.Hostname() + ":" + endpoint.Port() + "/docs"
	header := map[string]string{
		ingress.HTTPHeaderNameForDeployment: mainTestDeploymentName,
	}
	err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		out, err := rawhttp.RequestURL(http.MethodGet, u, header, nil)
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
	t.Parallel()
	err := waitForDeploymentToRunningState(mainTestDeploymentName)
	if err != nil {
		t.Fatalf("Expected deployment %s to be in running state, got %v", mainTestDeploymentName, err)
	}
	ld, err := lepton.Deployment().Get(mainTestDeploymentName)
	if err != nil {
		t.Fatal(err)
	}
	if ld.Status.Endpoint.ExternalEndpoint == "" {
		t.Fatal("Expected deployment to have an external endpoint, got empty string")
	}
	endpoint := ld.Status.Endpoint.ExternalEndpoint
	u, err := url.Parse(endpoint)
	if err != nil {
		t.Fatal("Expected the external endpoint to be a valid URL, got ", endpoint)
	}
	if err := waitForDNSPropagation(u.Hostname()); err != nil {
		t.Fatalf("Expected DNS to propagate for %s, got %v", u.Hostname(), err)
	}
	err = retryUntilNoErrorOrTimeout(time.Minute, func() error {
		out, err := rawhttp.RequestURL(http.MethodGet, endpoint+"/docs", nil, nil)
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

func TestIngressOfPublicDeployment(t *testing.T) {
	t.Parallel()
	if !*testDataPlaneRouting {
		t.Skip("Dataplane routing not ready")
	}
	dName := newName(t.Name())
	d := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
		Name:     dName,
		PhotonID: mainTestPhotonID,
		ResourceRequirement: leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
			ResourceShape: leptonaiv1alpha1.GP1HiddenTest,
			MinReplicas:   1,
		},
	}
	_, err := lepton.Deployment().Create(d)
	if err != nil {
		t.Fatal(err)
	}
	defer func() {
		err := lepton.Deployment().Delete(dName)
		if err != nil {
			t.Fatalf("Expected deployment %s to be deleted, got %v", dName, err)
		}
	}()
	err = waitForDeploymentToRunningState(dName)
	if err != nil {
		t.Fatalf("Expected deployment %s to be in running state, got %v", dName, err)
	}

	// access public deployment without an auth token
	ld, err := lepton.Deployment().Get(dName)
	if err != nil {
		t.Fatal(err)
	}
	endpoint := ld.Status.Endpoint.ExternalEndpoint
	if endpoint == "" {
		t.Fatal("Expected deployment to have an external endpoint, got empty string")
	}

	if err := testHostBasedIngress(dName, "", endpoint, true); err != nil {
		t.Fatal(err)
	}
	if err := testHeaderBasedIngress(dName, "", true); err != nil {
		t.Fatal(err)
	}
}

func TestIngressOfDeploymentWithCustomTokenAndUpdatingToken(t *testing.T) {
	t.Parallel()
	if !*testDataPlaneRouting {
		t.Skip("Dataplane routing not ready")
	}
	dName := newName(t.Name())
	token := newName(t.Name())
	d := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
		Name:     dName,
		PhotonID: mainTestPhotonID,
		ResourceRequirement: leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
			ResourceShape: leptonaiv1alpha1.GP1HiddenTest,
			MinReplicas:   1,
		},
		APITokens: []leptonaiv1alpha1.TokenVar{
			{
				Value: token,
			},
		},
	}
	_, err := lepton.Deployment().Create(d)
	if err != nil {
		t.Fatal(err)
	}
	defer func() {
		err := lepton.Deployment().Delete(dName)
		if err != nil {
			t.Fatalf("Expected deployment %s to be deleted, got %v", dName, err)
		}
	}()
	err = waitForDeploymentToRunningState(dName)
	if err != nil {
		t.Fatalf("Expected deployment %s to be in running state, got %v", mainTestDeploymentName, err)
	}

	ld, err := lepton.Deployment().Get(dName)
	if err != nil {
		t.Fatal(err)
	}
	endpoint := ld.Status.Endpoint.ExternalEndpoint
	if endpoint == "" {
		t.Fatal("Expected deployment to have an external endpoint, got empty string")
	}

	if err := testHostBasedIngress(dName, token, endpoint, true); err != nil {
		t.Fatal(err)
	}
	if err := testHeaderBasedIngress(dName, token, true); err != nil {
		t.Fatal(err)
	}
	if err := testHostBasedIngress(dName, "", endpoint, false); err == nil {
		t.Fatal("Expected host-based ingress to fail with empty token, but got access")
	}
	if err := testHeaderBasedIngress(dName, "", false); err == nil {
		t.Fatal("Expected header-based ingress to fail with empty token, but got access")
	}
	if err := testHostBasedIngress(dName, "wrong-token", endpoint, false); err == nil {
		t.Fatal("Expected host-based ingress to fail with wrong token, but got access")
	}
	if err := testHeaderBasedIngress(dName, "wrong-token'", false); err == nil {
		t.Fatal("Expected header-based ingress to fail with wrong token, but got access")
	}

	// Update to the new token
	newToken := newName(t.Name())
	newD := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
		Name: dName,
		APITokens: []leptonaiv1alpha1.TokenVar{
			{
				Value: newToken,
			},
		},
	}
	_, err = lepton.Deployment().Update(newD)
	if err != nil {
		t.Fatal(err)
	}
	err = waitForDeploymentToRunningState(dName)
	if err != nil {
		t.Fatalf("Expected deployment %s to be in running state, got %v", mainTestDeploymentName, err)
	}

	if err := testHostBasedIngress(dName, newToken, endpoint, true); err != nil {
		t.Fatal(err)
	}
	if err := testHeaderBasedIngress(dName, newToken, true); err != nil {
		t.Fatal(err)
	}
	if err := testHostBasedIngress(dName, token, endpoint, false); err == nil {
		t.Fatal("Expected host-based ingress to fail with old token, but got access")
	}
	if err := testHeaderBasedIngress(dName, token, false); err == nil {
		t.Fatal("Expected header-based ingress to fail with old token, but got access")
	}
	if err := testHostBasedIngress(dName, "", endpoint, false); err == nil {
		t.Fatal("Expected host-based ingress to fail with empty token, but got access")
	}
	if err := testHeaderBasedIngress(dName, "", false); err == nil {
		t.Fatal("Expected header-based ingress to fail with empty token, but got access")
	}
	if err := testHostBasedIngress(dName, "wrong-token", endpoint, false); err == nil {
		t.Fatal("Expected host-based ingress to fail with wrong token, but got access")
	}
	if err := testHeaderBasedIngress(dName, "wrong-token'", false); err == nil {
		t.Fatal("Expected header-based ingress to fail with wrong token, but got access")
	}
}

func testHostBasedIngress(dName, token, endpoint string, retry bool) error {
	h := goclient.NewHTTP(*workspaceURL, token)
	transport, err := getTransportFromURL(*workspaceURL)
	if err != nil {
		return err
	}
	testFun := func() error {
		out, err := h.RequestURLUntilWithCustomTransport(transport, http.MethodGet, endpoint+"/docs", nil, nil, 0, 0)
		if err != nil {
			return err
		}
		if len(out) == 0 {
			return fmt.Errorf("Expected non-empty response, got empty string")
		}
		return nil
	}
	if !retry {
		return testFun()
	}
	return retryUntilNoErrorOrTimeout(2*time.Minute, testFun)
}

func testHeaderBasedIngress(dName, token string, retry bool) error {
	h := goclient.NewHTTP(*workspaceURL, token)
	endpoint, err := url.Parse(*workspaceURL)
	if err != nil {
		return fmt.Errorf("Expected workspace URL to be a valid URL, got %s", *workspaceURL)
	}
	u := endpoint.Scheme + "://" + endpoint.Hostname() + ":" + endpoint.Port() + "/docs"
	header := map[string]string{
		ingress.HTTPHeaderNameForDeployment: dName,
	}
	testFun := func() error {
		out, err := h.RequestURL(http.MethodGet, u, header, nil)
		if err != nil {
			return err
		}
		if len(out) == 0 {
			return fmt.Errorf("Expected non-empty response, got empty string")
		}
		return nil
	}
	if !retry {
		return testFun()
	}
	return retryUntilNoErrorOrTimeout(2*time.Minute, testFun)
}

func getTransportFromURL(u string) (*http.Transport, error) {
	host, err := url.Parse(u)
	if err != nil {
		return nil, fmt.Errorf("Expected workspace URL to be a valid URL, got %s", u)
	}
	port := host.Port()
	if port == "" {
		if host.Scheme == "https" {
			port = "443"
		} else {
			port = "80"
		}
	}
	addr := host.Hostname() + ":" + port
	transport := &http.Transport{
		DialContext: func(_ context.Context, _, _ string) (net.Conn, error) {
			// Bypass DNS to make the test faster
			return net.Dial("tcp", addr)
		},
	}
	return transport, nil
}
