package ingress

const (
	IngressGroupOrderSSLRedirect  = 0
	IngressGroupOrderAllOptions   = 1
	IngressGroupOrderDeployment   = 100
	IngressGroupOrderAPIServer    = 900
	IngressGroupOrderUnauthorized = 950
	// IngressGroupOrderWeb is set in helm charts at /charts/template/web_ingress.yaml
	IngressGroupOrderWeb = 1000
)

// IngressName returns the name of the ingress for the deployment.
func IngressName(deploymentName string) string {
	return deploymentName + "-ingress"
}

// IngressNameForHeaderBased returns the name of the header-based ingress for the deployment.
func IngressNameForHeaderBased(deploymentName string) string {
	return deploymentName + "-header-ingress"
}

// IngressNameForHostBased returns the name of the host-based ingress for the deployment.
func IngressNameForHostBased(deploymentName string) string {
	return deploymentName + "-host-ingress"
}

// IngressGroupNameDeployment returns the name of the ingress group for the deployment.
func IngressGroupNameDeployment(namespace string) string {
	// TODO: separate control plane and deployment ingress groups.
	// TOOD: shard deployments into multiple ingress groups because each
	// ALB can only support 100 rules thus 100 deployments per ingress.
	return IngressGroupNameControlPlane(namespace)
}

// IngressGroupNameControlPlane returns the name of the ingress group for the control plane.
func IngressGroupNameControlPlane(namespace string) string {
	return "lepton-" + namespace + "-control-plane"
}
