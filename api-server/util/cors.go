package util

import (
	"fmt"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
)

var corsHeaders = map[string]string{
	"Access-Control-Allow-Credentials": "true",
	"Access-Control-Allow-Origin":      "https://dashboard.lepton.ai",
	"Access-Control-Allow-Methods":     "POST, PUT, HEAD, PATCH, GET, DELETE, OPTIONS",
	"Access-Control-Allow-Headers": "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, " +
		"Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, " +
		ingress.HTTPHeaderNameForAuthorization + ", " + ingress.HTTPHeaderNameForDeployment,
}

// SetCORSForDashboard sets the CORS headers for the response for dashboard.lepton.ai.
func SetCORSForDashboard(h http.Header) {
	for k, v := range corsHeaders {
		h.Set(k, v)
	}
}

// UnsetCORSForDashboard unsets the CORS headers for the response for dashboard.lepton.ai.
// This is for working around the header merging bug in the http reserve proxy package.
func UnsetCORSForDashboard(h http.Header) {
	h.Del("Access-Control-Allow-Credentials")
	h.Del("Access-Control-Allow-Origin")
	h.Del("Access-Control-Allow-Methods")
	h.Del("Access-Control-Allow-Headers")
}

// CheckCORSForDashboard checks the CORS headers for the response for dashboard.lepton.ai.
func CheckCORSForDashboard(h http.Header) error {
	for k, v := range corsHeaders {
		vs := h.Values(k)
		if len(vs) != 1 {
			return fmt.Errorf("CORS header %s is unepxected %s", k, vs)
		}

		if h.Get(k) != v {
			return fmt.Errorf("CORS header %s is not %s", k, v)
		}
	}

	return nil
}
