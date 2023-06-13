package goclient

import (
	"encoding/json"
	"net/http"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
)

const clusterPath = "/cluster"

type Cluster struct {
	HTTP *HTTP
}

func (l *Cluster) Info() (*httpapi.ClusterInfo, error) {
	output, err := l.HTTP.RequestPath(http.MethodGet, clusterPath, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := &httpapi.ClusterInfo{}
	if err := json.Unmarshal(output, ret); err != nil {
		return nil, err
	}
	return ret, nil
}
