package goclient

import (
	"encoding/json"
	"net/http"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
)

const instancesPath = "/instances"

type Instance struct {
	Lepton
}

func (l *Instance) List(deploymentID string) ([]httpapi.Instance, error) {
	output, err := l.HTTP.RequestPath(http.MethodGet, deploymentsPath+"/"+deploymentID+instancesPath, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := []httpapi.Instance{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}

// TODO: shell and log
