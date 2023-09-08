package e2etests

import (
	"net/http"
	"testing"

	goclient "github.com/leptonai/lepton/go-client"
)

func TestControlPlaneIngress(t *testing.T) {
	t.Parallel()
	path := "/workspace"
	// CORS
	_, err := goclient.NewHTTPWithCORS(*workspaceURL, *authToken).RequestPath(http.MethodGet, path, nil, nil)
	if err != nil {
		t.Fatalf("Expected access to workspace path with CORS %s, err %s", path, err)
	}

	// 404
	_, err = rawhttp.RequestPath(http.MethodGet, "/nonexisting", nil, nil)
	if err == nil {
		t.Fatalf("Expected error when requesting nonexisting path but got access")
	}

	// wrong token
	_, err = goclient.NewHTTP(*workspaceURL, "wrongtoken").RequestPath(http.MethodGet, path, nil, nil)
	if err == nil {
		t.Fatalf("Expected error when accessing with wrong token, but got access")
	}
}
