package main

import (
	"encoding/json"
	"strconv"
)

const (
	headerNameForDeployment           = "deployment"
	headerNameForAuthorization        = "Authorization"
	headerValueFormatForAuthorization = "Bearer %s"
)

type Annotation struct {
	annotation map[string]string
}

func NewAnnotation() *Annotation {
	annotation := map[string]string{
		"alb.ingress.kubernetes.io/scheme":           "internet-facing",
		"alb.ingress.kubernetes.io/target-type":      "ip",
		"alb.ingress.kubernetes.io/healthcheck-path": "/healthz",
	}
	if rootDomain != "" && certificateARN != "" {
		annotation["alb.ingress.kubernetes.io/listen-ports"] = `[{"HTTPS":443}]`
	}
	return &Annotation{
		annotation: annotation,
	}
}

func (a *Annotation) Add(key, value string) {
	a.annotation[key] = value
}

func (a *Annotation) Get() map[string]string {
	return a.annotation
}

func (a *Annotation) SetDomainNameAndSSLCert(domain, cert string) {
	if domain != "" {
		if cert != "" {
			a.annotation["alb.ingress.kubernetes.io/certificate-arn"] = cert
		}
		a.annotation["external-dns.alpha.kubernetes.io/hostname"] = domain
	}
}

func (a *Annotation) SetGroup(group string, order int) {
	a.annotation["alb.ingress.kubernetes.io/group.name"] = group
	// skip order if 0 because it is default to 0 and we cannot set it to 0
	if order > 0 {
		a.annotation["alb.ingress.kubernetes.io/group.order"] = strconv.Itoa(order)
	}
}

type HeaderCondition struct {
	Field            string `json:"field"`
	HttpHeaderConfig struct {
		HttpHeaderName string   `json:"httpHeaderName"`
		Values         []string `json:"values"`
	} `json:"httpHeaderConfig"`
}

// SetCondition sets the condition for the ingress rule, requiring len(headerNames) == len(headerValues)
func (a *Annotation) SetConditions(serviceName string, headerNames []string, headerValues [][]string) {
	headerConditions := make([]HeaderCondition, len(headerNames))
	for i := range headerNames {
		headerConditions[i].Field = "http-header"
		headerConditions[i].HttpHeaderConfig.HttpHeaderName = headerNames[i]
		headerConditions[i].HttpHeaderConfig.Values = headerValues[i]
	}
	value, err := json.Marshal(headerConditions)
	if err != nil {
		a.annotation["alb.ingress.kubernetes.io/conditions."+serviceName] = string(value)
	}
}

func (a *Annotation) SetDeploymentConditions(serviceName, deploymentName string) {
	a.SetConditions(serviceName,
		[]string{headerNameForDeployment},
		[][]string{{deploymentName}})
}

func (a *Annotation) SetAPITokenConditions(serviceName, apiToken string) {
	if apiToken == "" {
		return
	}
	a.SetConditions(serviceName,
		[]string{headerNameForAuthorization},
		[][]string{{headerValueFormatForAuthorization}})
}

func (a *Annotation) SetDeploymentAndAPITokenConditions(serviceName, deploymentName, apiToken string) {
	if apiToken == "" {
		a.SetDeploymentConditions(serviceName, deploymentName)
		return
	}
	a.SetConditions(serviceName,
		[]string{headerNameForDeployment, headerNameForAuthorization},
		[][]string{{deploymentName}, {apiToken}})
}

func (a *Annotation) SetActions(serviceName string, actions string) {
	a.annotation["alb.ingress.kubernetes.io/actions."+serviceName] = actions
}
