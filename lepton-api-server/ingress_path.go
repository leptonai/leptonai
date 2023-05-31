package main

import networkingv1 "k8s.io/api/networking/v1"

type PrefixPaths struct {
	paths []networkingv1.HTTPIngressPath
}

func NewPrefixPaths() *PrefixPaths {
	return &PrefixPaths{}
}

func (p *PrefixPaths) Get() []networkingv1.HTTPIngressPath {
	return p.paths
}

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
