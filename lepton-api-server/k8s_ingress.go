package main

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"

	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var (
	ingressNamespace = "default"
	certificateARN   = ""
	rootDomain       = ""
)

const apiServerIngressName = "lepton-api-server-ingress"

const headerKeyForLeptonDeploymentRerouting = "deployment"

func deploymentIngressName(ld *httpapi.LeptonDeployment) string {
	return "ld-" + ld.Name + "-ingress"
}

func deploymentIngressGroupName(ld *httpapi.LeptonDeployment) string {
	// TODO: separate control plane and deployment ingress groups.
	// TOOD: shard deployments into multiple ingress groups because each
	// ALB can only support 100 rules thus 100 deployments per ingress.
	return controlPlaneIngressGroupName()
}

func controlPlaneIngressGroupName() string {
	return "lepton-" + ingressNamespace + "-control-plane"
}

func createDeploymentIngress(ld *httpapi.LeptonDeployment, or metav1.OwnerReference) error {
	clientset := util.MustInitK8sClientSet()

	albstr := "alb"
	// Define Ingress object
	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:            deploymentIngressName(ld),
			Namespace:       ingressNamespace,
			Annotations:     newDeploymentIngressAnnotation(ld),
			OwnerReferences: []metav1.OwnerReference{or},
		},
		Spec: networkingv1.IngressSpec{
			IngressClassName: &albstr,
			Rules: []networkingv1.IngressRule{
				// TODO: add host based routing for custom domains.
				{
					IngressRuleValue: networkingv1.IngressRuleValue{
						HTTP: &networkingv1.HTTPIngressRuleValue{
							Paths: []networkingv1.HTTPIngressPath{
								newHTTPIngressPath(serviceName(ld), servicePort, "/", networkingv1.PathTypePrefix),
							},
						},
					},
				},
			},
		},
	}

	// Create Ingress
	result, err := clientset.NetworkingV1().Ingresses(ingressNamespace).Create(context.Background(), ingress, metav1.CreateOptions{})
	if err != nil {
		return err
	}
	fmt.Printf("Created Ingress %q.\n", result.GetObjectMeta().GetName())

	return nil
}

func newHTTPIngressPath(serviceName string, servicePort int32, path string, pathType networkingv1.PathType) networkingv1.HTTPIngressPath {
	return networkingv1.HTTPIngressPath{
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
	}
}

func newDeploymentIngressAnnotation(ld *httpapi.LeptonDeployment) map[string]string {
	annotation := map[string]string{
		"alb.ingress.kubernetes.io/scheme":                        "internet-facing",
		"alb.ingress.kubernetes.io/target-type":                   "ip",
		"alb.ingress.kubernetes.io/healthcheck-path":              "/healthz",
		"alb.ingress.kubernetes.io/group.name":                    deploymentIngressGroupName(ld),
		"alb.ingress.kubernetes.io/conditions." + serviceName(ld): fmt.Sprintf(`[{"field":"http-header","httpHeaderConfig":{"httpHeaderName":"%s","values":["%s"]}}]`, headerKeyForLeptonDeploymentRerouting, ld.Name),
	}
	if rootDomain != "" {
		annotation["external-dns.alpha.kubernetes.io/hostname"] = ld.DomainName(rootDomain)
		if certificateARN != "" {
			annotation["alb.ingress.kubernetes.io/listen-ports"] = `[{"HTTPS":443}]`
			annotation["alb.ingress.kubernetes.io/certificate-arn"] = certificateARN
		}
	}
	return annotation
}

func newAPIServerIngressAnnotation() map[string]string {
	annotation := map[string]string{
		"alb.ingress.kubernetes.io/scheme":           "internet-facing",
		"alb.ingress.kubernetes.io/target-type":      "ip",
		"alb.ingress.kubernetes.io/healthcheck-path": "/healthz",
		"alb.ingress.kubernetes.io/group.name":       controlPlaneIngressGroupName(),
		// Setting the group.order to be higher priority than web (1000), and lower than lepton deployment (0)
		"alb.ingress.kubernetes.io/group.order": "900",
	}
	if rootDomain != "" {
		if certificateARN != "" {
			annotation["alb.ingress.kubernetes.io/listen-ports"] = `[{"HTTPS":443}]`
			annotation["alb.ingress.kubernetes.io/certificate-arn"] = certificateARN
		}
		annotation["external-dns.alpha.kubernetes.io/hostname"] = rootDomain
	}
	return annotation
}

func mustUpdateAPIServerIngress() {
	clientset := util.MustInitK8sClientSet()

	albstr := "alb"
	// Define Ingress object
	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:        apiServerIngressName,
			Namespace:   ingressNamespace,
			Annotations: newAPIServerIngressAnnotation(),
		},
		Spec: networkingv1.IngressSpec{
			IngressClassName: &albstr,
			Rules: []networkingv1.IngressRule{
				{
					IngressRuleValue: networkingv1.IngressRuleValue{
						HTTP: &networkingv1.HTTPIngressRuleValue{
							Paths: []networkingv1.HTTPIngressPath{
								newHTTPIngressPath("lepton-api-server-service", apiServerPort, "/api/", networkingv1.PathTypePrefix),
							},
						},
					},
				},
			},
		},
	}

	// Update api-server Ingress
	result, err := clientset.NetworkingV1().Ingresses(ingressNamespace).Update(context.Background(), ingress, metav1.UpdateOptions{})
	if err != nil {
		panic(err)
	}

	fmt.Printf("Updated Ingress %q.\n", result.GetObjectMeta().GetName())
}
