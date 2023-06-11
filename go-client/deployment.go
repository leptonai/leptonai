package goclient

import (
	"encoding/json"
	"net/http"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

const deploymentsPath = "/deployments"

type Deployment struct {
	HTTP *HTTP
}

func (l *Deployment) Create(d *leptonaiv1alpha1.LeptonDeploymentUserSpec) (*httpapi.LeptonDeployment, error) {
	body, err := json.Marshal(d)
	if err != nil {
		return nil, err
	}
	header := map[string]string{
		"Content-Type": "application/json",
	}
	output, err := l.HTTP.Request(http.MethodPost, deploymentsPath, header, body)
	if err != nil {
		return nil, err
	}
	ret := &httpapi.LeptonDeployment{}
	if err := json.Unmarshal(output, ret); err != nil {
		return nil, err
	}
	return ret, nil
}

func (l *Deployment) List() ([]httpapi.LeptonDeployment, error) {
	output, err := l.HTTP.Request(http.MethodGet, deploymentsPath, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := []httpapi.LeptonDeployment{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}

func (l *Deployment) Get(id string) (*httpapi.LeptonDeployment, error) {
	output, err := l.HTTP.Request(http.MethodGet, deploymentsPath+"/"+id, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := &httpapi.LeptonDeployment{}
	if err := json.Unmarshal(output, ret); err != nil {
		return nil, err
	}
	return ret, nil
}

func (l *Deployment) Delete(id string) error {
	_, err := l.HTTP.Request(http.MethodDelete, deploymentsPath+"/"+id, nil, nil)
	if err != nil {
		return err
	}
	return nil
}

func (l *Deployment) Update(d *leptonaiv1alpha1.LeptonDeploymentUserSpec) (*httpapi.LeptonDeployment, error) {
	body, err := json.Marshal(d)
	if err != nil {
		return nil, err
	}
	header := map[string]string{
		"Content-Type": "application/json",
	}
	output, err := l.HTTP.Request(http.MethodPatch, deploymentsPath+"/"+d.Name, header, body)
	if err != nil {
		return nil, err
	}
	ret := &httpapi.LeptonDeployment{}
	if err := json.Unmarshal(output, ret); err != nil {
		return nil, err
	}
	return ret, nil
}
