package main

import (
	"context"
	"fmt"
	"strings"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"

	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var (
	ingressNamespace = "default"
	certificateARN   = ""
	rootDomain       = ""
)

const headerKeyForLeptonDeploymentRerouting = "deployment"

func ingressName(ld *httpapi.LeptonDeployment) string {
	return ld.Name + "-ingress"
}

func updateLeptonIngress(lds []*httpapi.LeptonDeployment) error {
	// Create a Kubernetes client
	clientset := mustInitK8sClientSet()

	// List all current ingresses
	ingresses, err := clientset.NetworkingV1().Ingresses(ingressNamespace).List(context.Background(), metav1.ListOptions{})
	if err != nil {
		return err
	}

	for _, ingress := range ingresses.Items {
		// Find the ingress that matches the deployment
		// TODO: fix the hard coding of ingress name
		if ingress.Name == "lepton-ingress" || ingress.Name == "lepton-tf-ingress" {
			originPaths := ingress.Spec.Rules[0].IngressRuleValue.HTTP.Paths
			// Additional 2 ingress rulePaths for the lepton api and web
			rulePaths := make([]networkingv1.HTTPIngressPath, 0, len(lds)+2)
			// clean up the ingress annotations
			for key := range ingress.Annotations {
				if strings.HasPrefix(key, "alb.ingress.kubernetes.io/conditions.") {
					delete(ingress.Annotations, key)
				}
			}
			rulePaths = append(rulePaths, newHTTPRedirectSSLIngressPath())
			for _, ld := range lds {
				key, value := newAnnotationKeyValueForHeaderBasedRouting(ld)
				ingress.Annotations[key] = value
				rulePaths = append(rulePaths, newHTTPIngressPath(serviceName(ld), servicePort, "/", networkingv1.PathTypePrefix))
			}
			rulePaths = append(rulePaths, originPaths[len(originPaths)-2:]...)
			ingress.Spec.Rules[0].IngressRuleValue.HTTP.Paths = rulePaths

			// Update the ingress
			_, err = clientset.NetworkingV1().Ingresses(ingressNamespace).Update(context.Background(), &ingress, metav1.UpdateOptions{})
			if err != nil {
				return err
			}
		}
	}
	return nil
}

func createDeploymentIngress(ld *httpapi.LeptonDeployment, or metav1.OwnerReference) error {
	// Create a Kubernetes client
	clientset := mustInitK8sClientSet()

	albstr := "alb"
	// Define Ingress object
	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:            ingressName(ld),
			Namespace:       ingressNamespace,
			Annotations:     newDeploymentIngressAnnotation(ld),
			OwnerReferences: []metav1.OwnerReference{or},
		},
		Spec: networkingv1.IngressSpec{
			IngressClassName: &albstr,
			Rules: []networkingv1.IngressRule{
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

func watchForDeploymentIngressEndpoint(name string) (string, error) {
	// Create a Kubernetes client
	clientset := mustInitK8sClientSet()

	// Watch for Ingress IP
	watcher, err := clientset.NetworkingV1().Ingresses(ingressNamespace).Watch(context.Background(), metav1.ListOptions{})
	if err != nil {
		return "", err
	}

	// Wait for Ingress IP
	for event := range watcher.ResultChan() {
		ingress, ok := event.Object.(*networkingv1.Ingress)
		if !ok {
			err = fmt.Errorf("unexpected type %T", event.Object)
			return "", err
		}

		if ingress.Name == name {
			if len(ingress.Status.LoadBalancer.Ingress) > 0 {
				return ingress.Status.LoadBalancer.Ingress[0].Hostname, nil
			}
		}
	}

	return "", nil
}

func newHTTPRedirectSSLIngressPath() networkingv1.HTTPIngressPath {
	pathType := networkingv1.PathTypePrefix
	return networkingv1.HTTPIngressPath{
		Path:     "/",
		PathType: &pathType,
		Backend: networkingv1.IngressBackend{
			Service: &networkingv1.IngressServiceBackend{
				Name: "ssl-redirect",
				Port: networkingv1.ServiceBackendPort{
					Name: "use-annotation",
				},
			},
		},
	}
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

func newAnnotationKeyValueForHeaderBasedRouting(ld *httpapi.LeptonDeployment) (key string, value string) {
	key = "alb.ingress.kubernetes.io/conditions." + serviceName(ld)
	value = fmt.Sprintf(`[{"field":"http-header","httpHeaderConfig":{"httpHeaderName":"%s","values":["%s"]}}]`, headerKeyForLeptonDeploymentRerouting, ld.Name)
	return
}

func newDeploymentIngressAnnotation(ld *httpapi.LeptonDeployment) map[string]string {
	annotation := map[string]string{
		"alb.ingress.kubernetes.io/scheme":           "internet-facing",
		"alb.ingress.kubernetes.io/target-type":      "ip",
		"alb.ingress.kubernetes.io/healthcheck-path": "/healthz",
	}
	if rootDomain != "" {
		annotation["external-dns.alpha.kubernetes.io/hostname"] = fmt.Sprintf("%s.%s", ld.Name, rootDomain)
		if certificateARN != "" {
			annotation["alb.ingress.kubernetes.io/listen-ports"] = `[{"HTTPS":443}, {"HTTP":80}]`
			annotation["alb.ingress.kubernetes.io/actions.ssl-redirect"] = `{"Type": "redirect", "RedirectConfig": { "Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}`
			annotation["alb.ingress.kubernetes.io/certificate-arn"] = certificateARN
		}
	}
	return annotation
}
