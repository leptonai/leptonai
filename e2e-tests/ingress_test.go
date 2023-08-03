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
	h := goclient.NewHTTP(*workspaceURL, "")
	ld, err := lepton.Deployment().Get(dName)
	if err != nil {
		t.Fatal(err)
	}
	if ld.Status.Endpoint.ExternalEndpoint == "" {
		t.Fatal("Expected deployment to have an external endpoint, got empty string")
	}

	{ // Test host based ingress
		transport, err := getTransportFromURL(*workspaceURL)
		if err != nil {
			t.Fatal(err)
		}
		endpoint := ld.Status.Endpoint.ExternalEndpoint
		err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
			out, err := h.RequestURLUntilWithCustomTransport(transport, http.MethodGet, endpoint+"/docs", nil, nil, 0, 0)
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

	{ // Test header based ingress
		endpoint, err := url.Parse(*workspaceURL)
		if err != nil {
			t.Fatalf("Expected workspace URL to be a valid URL, got %s", *workspaceURL)
		}
		u := endpoint.Scheme + "://" + endpoint.Hostname() + ":" + endpoint.Port() + "/docs"
		header := map[string]string{
			ingress.HTTPHeaderNameForDeployment: dName,
		}
		err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
			out, err := h.RequestURL(http.MethodGet, u, header, nil)
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
}

func TestIngressOfDeploymentWithCustomToken(t *testing.T) {
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
	// access deployment with the custom token
	h := goclient.NewHTTP(*workspaceURL, token)
	ld, err := lepton.Deployment().Get(dName)
	if err != nil {
		t.Fatal(err)
	}
	if ld.Status.Endpoint.ExternalEndpoint == "" {
		t.Fatal("Expected deployment to have an external endpoint, got empty string")
	}

	{ // Test host based ingress
		transport, err := getTransportFromURL(*workspaceURL)
		if err != nil {
			t.Fatal(err)
		}
		endpoint := ld.Status.Endpoint.ExternalEndpoint
		err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
			out, err := h.RequestURLUntilWithCustomTransport(transport, http.MethodGet, endpoint+"/docs", nil, nil, 0, 0)
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

	{ // Test header based ingress
		endpoint, err := url.Parse(*workspaceURL)
		if err != nil {
			t.Fatalf("Expected workspace URL to be a valid URL, got %s", *workspaceURL)
		}
		u := endpoint.Scheme + "://" + endpoint.Hostname() + ":" + endpoint.Port() + "/docs"
		header := map[string]string{
			ingress.HTTPHeaderNameForDeployment: dName,
		}
		err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
			out, err := h.RequestURL(http.MethodGet, u, header, nil)
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