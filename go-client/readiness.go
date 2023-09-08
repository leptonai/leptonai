package goclient

import (
	"encoding/json"
	"net/http"

	"github.com/leptonai/lepton/api-server/httpapi"
)

type Readiness struct {
	Lepton
}

func (l *Readiness) GetDeploymentReadinessIssue(id string) (httpapi.DeploymentReadinessIssue, error) {
	output, err := l.http.RequestPath(http.MethodGet, deploymentsPath+"/"+id+"/readiness", nil, nil)
	if err != nil {
		return nil, err
	}
	ret := httpapi.DeploymentReadinessIssue{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}
