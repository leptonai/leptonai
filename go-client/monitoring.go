package goclient

import "net/http"

const monitoringPath = "/monitoring"

type Monitoring struct {
	HTTP *HTTP
}

func (l *Monitoring) GetDeploymentRaw(metricName, deploymentID string) (string, error) {
	output, err := l.HTTP.Request(http.MethodGet, deploymentsPath+"/"+deploymentID+monitoringPath+"/"+metricName, nil, nil)
	if err != nil {
		return "", err
	}
	return string(output), nil
}

func (l *Monitoring) GetInstanceRaw(metricName, deploymentID, instanceID string) (string, error) {
	output, err := l.HTTP.Request(http.MethodGet, deploymentsPath+"/"+deploymentID+instancesPath+"/"+instanceID+monitoringPath+"/"+metricName, nil, nil)
	if err != nil {
		return "", err
	}
	return string(output), nil
}
