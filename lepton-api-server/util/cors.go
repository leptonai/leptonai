package util

import (
	"net/http"

	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
)

// SetCORSForDashboard sets the CORS headers for the response for dashboard.lepton.ai.
func SetCORSForDashboard(h http.Header) {
	// Add the CORS headers after the request is handled to avoid duplication.
	h.Set("Access-Control-Allow-Credentials", "true")
	h.Set("Access-Control-Allow-Origin", "https://dashboard.lepton.ai")
	h.Set("Access-Control-Allow-Methods",
		"POST, PUT, HEAD, PATCH, GET, DELETE, OPTIONS")
	h.Set("Access-Control-Allow-Headers",
		"X-CSRF-Token, X-Requested-With, Accept, Accept-Version, "+
			"Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, "+
			ingress.HTTPHeaderNameForAuthorization+", "+
			ingress.HTTPHeaderNameForDeployment)
}
