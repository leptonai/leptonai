package goclient

import (
	"net/http"
)

const monitoringPath = "/monitoring"

type Monitoring struct {
	Lepton
}

func (l *Monitoring) GetDeploymentRaw(metricName, deploymentID string) (string, error) {
	output, err := l.http.RequestPath(http.MethodGet, deploymentsPath+"/"+deploymentID+monitoringPath+"/"+metricName, nil, nil)
	if err != nil {
		return "", err
	}
	return string(output), nil
}

func (l *Monitoring) GetReplicaRaw(metricName, deploymentID, replicaID string) (string, error) {
	output, err := l.http.RequestPath(http.MethodGet, deploymentsPath+"/"+deploymentID+replicasPath+"/"+replicaID+monitoringPath+"/"+metricName, nil, nil)
	if err != nil {
		return "", err
	}
	return string(output), nil
}
