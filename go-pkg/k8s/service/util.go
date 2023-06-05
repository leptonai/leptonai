package service

const (
	// Port is the default port for a service
	Port = 8080
	// RootPath is the default root path for a service
	RootPath = "/"
)

// ServiceName returns the name of the service for a deployment
func ServiceName(deploymentName string) string {
	return deploymentName + "-service"
}
