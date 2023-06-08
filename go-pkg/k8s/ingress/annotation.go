package ingress

import (
	"encoding/json"
	"strconv"
)

const (
	HTTPHeaderNameForDeployment    = "Deployment"
	HTTPHeaderNameForAuthorization = "Authorization"
)

// Annotation is a wrapper for the annotations used in the ingress
type Annotation struct {
	domainName     string
	certificateARN string
	annotations    map[string]string
}

// NewAnnotation returns a new Annotation
func NewAnnotation(domainName, certificateARN string) *Annotation {
	annotation := map[string]string{
		"alb.ingress.kubernetes.io/scheme":           "internet-facing",
		"alb.ingress.kubernetes.io/target-type":      "ip",
		"alb.ingress.kubernetes.io/healthcheck-path": "/healthz",
	}
	if domainName != "" && certificateARN != "" {
		annotation["alb.ingress.kubernetes.io/listen-ports"] = `[{"HTTPS":443}]`
	}
	return &Annotation{
		domainName:     domainName,
		certificateARN: certificateARN,
		annotations:    annotation,
	}
}

// Add adds a new annotation key value pair
func (a *Annotation) Add(key, value string) *Annotation {
	a.annotations[key] = value
	return a
}

// Get returns the annotations
func (a *Annotation) Get() map[string]string {
	return a.annotations
}

// SetDomainNameAndSSLCert sets the domain name and SSL certificate
func (a *Annotation) SetDomainNameAndSSLCert() *Annotation {
	if a.domainName != "" {
		if a.certificateARN != "" {
			a.annotations["alb.ingress.kubernetes.io/certificate-arn"] = a.certificateARN
		}
		a.annotations["external-dns.alpha.kubernetes.io/hostname"] = a.domainName
	}
	return a
}

// SetGroup sets the group name and order used to determine the priority of the ingress rules
func (a *Annotation) SetGroup(group string, order int) *Annotation {
	a.annotations["alb.ingress.kubernetes.io/group.name"] = group
	// skip order if 0 because it is default to 0 and we cannot set it to 0
	if order > 0 {
		a.annotations["alb.ingress.kubernetes.io/group.order"] = strconv.Itoa(order)
	}
	return a
}

// HeaderCondition defines the condition for the HTTP header config.
type HeaderCondition struct {
	Field            string `json:"field"`
	HTTPHeaderConfig struct {
		HTTPHeaderName string   `json:"httpHeaderName"`
		Values         []string `json:"values"`
	} `json:"httpHeaderConfig"`
}

// SetCondition sets the condition for the ingress rule, requiring len(headerNames) == len(headerValues)
func (a *Annotation) SetConditions(serviceName string, headerNames []string, headerValues [][]string) *Annotation {
	headerConditions := make([]HeaderCondition, len(headerNames))
	for i := range headerNames {
		headerConditions[i].Field = "http-header"
		headerConditions[i].HTTPHeaderConfig.HTTPHeaderName = headerNames[i]
		headerConditions[i].HTTPHeaderConfig.Values = headerValues[i]
	}
	value, err := json.Marshal(headerConditions)
	if err != nil {
		return a
	}
	a.annotations["alb.ingress.kubernetes.io/conditions."+serviceName] = string(value)
	return a
}

// SetDeploymentConditions sets the header-based routing condition for the ingress rule
func (a *Annotation) SetDeploymentConditions(serviceName, deploymentName string) *Annotation {
	a.SetConditions(serviceName,
		[]string{HTTPHeaderNameForDeployment},
		[][]string{{deploymentName}})
	return a
}

// SetAPITokenConditions sets the static API token condition for the ingress rule
func (a *Annotation) SetAPITokenConditions(serviceName string, apiTokens []string) *Annotation {
	if len(apiTokens) == 0 {
		return a
	}
	a.SetConditions(serviceName,
		[]string{HTTPHeaderNameForAuthorization},
		[][]string{addBearerToTokens(apiTokens)})
	return a
}

// SetDeploymentAndAPITokenConditions sets the API token and header-based routing condition for the ingress rule
func (a *Annotation) SetDeploymentAndAPITokenConditions(serviceName, deploymentName string, apiTokens []string) *Annotation {
	if len(apiTokens) == 0 {
		a.SetDeploymentConditions(serviceName, deploymentName)
		return a
	}
	a.SetConditions(serviceName,
		[]string{HTTPHeaderNameForDeployment, HTTPHeaderNameForAuthorization},
		[][]string{{deploymentName}, addBearerToTokens(apiTokens)})
	return a
}

// SetActions sets the actions for the ingress rule
func (a *Annotation) SetActions(serviceName string, actions string) *Annotation {
	a.annotations["alb.ingress.kubernetes.io/actions."+serviceName] = actions
	return a
}

func addBearerToTokens(tokens []string) []string {
	for i := range tokens {
		tokens[i] = "Bearer " + tokens[i]
	}
	return tokens
}
