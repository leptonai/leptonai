package util

import (
	"encoding/json"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"
)

// ListClusters lists all the lepton clusters.
func ListClusters(c *goclient.HTTP) ([]*crdv1alpha1.LeptonCluster, error) {
	b, err := ListClustersRaw(c)
	if err != nil {
		return nil, err
	}

	var rs []*crdv1alpha1.LeptonCluster
	if err = json.Unmarshal(b, &rs); err != nil {
		return nil, err
	}

	return rs, nil
}

// ListClustersRaw lists all the lepton clusters in raw json.
func ListClustersRaw(c *goclient.HTTP) ([]byte, error) {
	b, err := c.RequestPath(http.MethodGet, "/clusters", nil, nil)
	if err != nil {
		return nil, err
	}

	return b, nil
}
