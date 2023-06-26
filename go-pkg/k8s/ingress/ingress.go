package ingress

import (
	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// IngressGroupNameDeployment returns the ingress based on given annotations and paths
func NewIngress(name, namespace, hostName string, annotations map[string]string, paths []networkingv1.HTTPIngressPath, or []metav1.OwnerReference) *networkingv1.Ingress {
	albstr := "alb"
	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:            name,
			Namespace:       namespace,
			Annotations:     annotations,
			OwnerReferences: or,
		},
		Spec: networkingv1.IngressSpec{
			IngressClassName: &albstr,
			Rules: []networkingv1.IngressRule{
				{
					IngressRuleValue: networkingv1.IngressRuleValue{
						HTTP: &networkingv1.HTTPIngressRuleValue{
							Paths: paths,
						},
					},
				},
			},
		},
	}
	if len(hostName) != 0 {
		ingress.Spec.Rules[0].Host = hostName
	}
	return ingress
}
