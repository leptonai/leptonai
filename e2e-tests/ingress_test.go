package e2etests

import (
	"net/http"
	"net/url"
	"testing"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

func TestIngressWithDeploymentDocsUsingHeaderBased(t *testing.T) {
	err := waitForDeploymentToRunningState(mainTestDeploymentID)
	if err != nil {
		t.Fatalf("Expected deployment %s to be in running state, got %v", mainTestDeploymentID, err)
	}
	endpoint, err := url.Parse(*workspaceURL)
	if err != nil {
		t.Fatalf("Expected workspace URL to be a valid URL, got %s", *workspaceURL)
	}
	u := endpoint.Scheme + "://" + endpoint.Hostname() + ":" + endpoint.Port() + "/docs"
	header := map[string]string{
		ingress.HTTPHeaderNameForDeployment: mainTestDeploymentID,
	}
	err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		out, err := lepton.HTTP.RequestURL(http.MethodGet, u, header, nil)
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
	err := waitForDeploymentToRunningState(mainTestDeploymentID)
	if err != nil {
		t.Fatalf("Expected deployment %s to be in running state, got %v", mainTestDeploymentID, err)
	}
	ld, err := lepton.Deployment().Get(mainTestDeploymentID)
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
		endpoint := ld.Status.Endpoint.ExternalEndpoint
		u, err := url.Parse(endpoint)
		if err != nil {
			t.Fatal("Expected the external endpoint to be a valid URL, got ", endpoint)
		}
		if err := waitForDNSPropagation(u.Hostname()); err != nil {
			t.Fatalf("Expected DNS to propagate for %s, got %v", u.Hostname(), err)
		}
		err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
			out, err := h.RequestURL(http.MethodGet, endpoint+"/docs", nil, nil)
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
		t.Fatalf("Expected deployment %s to be in running state, got %v", mainTestDeploymentID, err)
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
		endpoint := ld.Status.Endpoint.ExternalEndpoint
		u, err := url.Parse(endpoint)
		if err != nil {
			t.Fatal("Expected the external endpoint to be a valid URL, got ", endpoint)
		}
		if err := waitForDNSPropagation(u.Hostname()); err != nil {
			t.Fatalf("Expected DNS to propagate for %s, got %v", u.Hostname(), err)
		}
		err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
			out, err := h.RequestURL(http.MethodGet, endpoint+"/docs", nil, nil)
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
