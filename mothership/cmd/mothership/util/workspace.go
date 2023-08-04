package util

import (
	"encoding/json"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"
)

// ListWorkspaces lists all the lepton workspaces.
func ListWorkspaces(c *goclient.HTTP) ([]*crdv1alpha1.LeptonWorkspace, error) {
	b, err := ListWorkspacesRaw(c)
	if err != nil {
		return nil, err
	}

	var rs []*crdv1alpha1.LeptonWorkspace
	if err = json.Unmarshal(b, &rs); err != nil {
		return nil, err
	}

	return rs, nil
}

// ListWorkspacesRaw lists all the lepton workspaces in raw json.
func ListWorkspacesRaw(c *goclient.HTTP) ([]byte, error) {
	b, err := c.RequestPath(http.MethodGet, "/workspaces", nil, nil)
	if err != nil {
		return nil, err
	}

	return b, nil
}
