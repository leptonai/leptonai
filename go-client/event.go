package goclient

import (
	"encoding/json"
	"net/http"

	"github.com/leptonai/lepton/api-server/httpapi"
)

type Event struct {
	Lepton
}

func (l *Event) GetDeploymentEvents(id string) ([]httpapi.LeptonDeploymentEvent, error) {
	output, err := l.http.RequestPath(http.MethodGet, deploymentsPath+"/"+id+"/events", nil, nil)
	if err != nil {
		return nil, err
	}
	ret := []httpapi.LeptonDeploymentEvent{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}
