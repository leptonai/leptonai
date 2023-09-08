package ingress

import (
	networkingv1 "k8s.io/api/networking/v1"
)

// PrefixPaths is a wrapper for networkingv1.HTTPIngressPath
type PrefixPaths struct {
	paths []networkingv1.HTTPIngressPath
}

// NewPrefixPaths returns a new PrefixPaths
func NewPrefixPaths() *PrefixPaths {
	return &PrefixPaths{}
}

// Get returns the paths
func (p *PrefixPaths) Get() []networkingv1.HTTPIngressPath {
	return p.paths
}

// AddServicePath adds a new path for a service
func (p *PrefixPaths) AddServicePath(serviceName string, servicePort int32, path string) *PrefixPaths {
	pathType := networkingv1.PathTypePrefix
	p.paths = append(p.paths,
		networkingv1.HTTPIngressPath{
			Path:     path,
			PathType: &pathType,
			Backend: networkingv1.IngressBackend{
				Service: &networkingv1.IngressServiceBackend{
					Name: serviceName,
					Port: networkingv1.ServiceBackendPort{
						Number: servicePort,
					},
				},
			},
		},
	)
	return p
}

// AddAnnotationPath adds a new path for an annotation-defined service, e.g., https redirect.
func (p *PrefixPaths) AddAnnotationPath(serviceName string, path string) *PrefixPaths {
	pathType := networkingv1.PathTypePrefix
	p.paths = append(p.paths,
		networkingv1.HTTPIngressPath{
			Path:     path,
			PathType: &pathType,
			Backend: networkingv1.IngressBackend{
				Service: &networkingv1.IngressServiceBackend{
					Name: serviceName,
					Port: networkingv1.ServiceBackendPort{
						Name: "use-annotation",
					},
				},
			},
		},
	)
	return p
}
