package goclient

import (
	"encoding/json"
	"net/http"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
)

const workspacePath = "/workspace"

type Workspace struct {
	Lepton
}

func (l *Workspace) Info() (*httpapi.WorkspaceInfo, error) {
	output, err := l.HTTP.RequestPath(http.MethodGet, workspacePath, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := &httpapi.WorkspaceInfo{}
	if err := json.Unmarshal(output, ret); err != nil {
		return nil, err
	}
	return ret, nil
}
