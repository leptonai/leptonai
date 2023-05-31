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
	apiToken         = ""
)

const (
	// TODO: remove the hard coding, pass in something and calculate the name
	apiServerIngressName = "lepton-api-server-ingress"
	apiServerServiceName = "lepton-api-server-service"

	serviceNameForUnauthorizedDeployment = "response-401-deployment"
	serviceNameForUnauthorizedAPIServer  = "response-401-apiserver"
	ingressNameForUnauthorizedAccess     = "response-401-ingress"

	unauthorizedAction = `{"type":"fixed-response","fixedResponseConfig":{"contentType":"text/plain","statusCode":"401","messageBody":"Not Authorized"}}`
)

const (
	GroupOrderDeployment   = 0
	GroupOrderAPIServer    = 900
	GroupOrderUnauthorized = 950
	// GroupOrderWeb is set in helm charts at /charts/template/web_ingress.yaml
	GroupOrderWeb = 1000
)

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
	annotation := NewAnnotation()
	annotation.SetGroup(deploymentIngressGroupName(ld), GroupOrderDeployment)
	annotation.SetDeploymentAndAPITokenConditions(serviceName(ld), ld.Name, apiToken)
	annotation.SetDomainNameAndSSLCert(fmt.Sprintf("%s.%s", ld.Name, rootDomain), certificateARN)

	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:            deploymentIngressName(ld),
			Namespace:       ingressNamespace,
			Annotations:     annotation.Get(),
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

func newActionIngressPathPrefix(serviceName, path string) networkingv1.HTTPIngressPath {
	pathType := networkingv1.PathTypePrefix
	return networkingv1.HTTPIngressPath{
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
	}
}

func mustUpdateAPIServerIngress() {
	clientset := util.MustInitK8sClientSet()

	albstr := "alb"

	annotation := NewAnnotation()
	annotation.SetGroup(controlPlaneIngressGroupName(), GroupOrderAPIServer)
	annotation.SetAPITokenConditions(apiServerServiceName, apiToken)
	annotation.SetDomainNameAndSSLCert(rootDomain, certificateARN)

	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:        apiServerIngressName,
			Namespace:   ingressNamespace,
			Annotations: annotation.Get(),
		},
		Spec: networkingv1.IngressSpec{
			IngressClassName: &albstr,
			Rules: []networkingv1.IngressRule{
				{
					IngressRuleValue: networkingv1.IngressRuleValue{
						HTTP: &networkingv1.HTTPIngressRuleValue{
							Paths: []networkingv1.HTTPIngressPath{
								newHTTPIngressPath(apiServerServiceName, apiServerPort, "/api/", networkingv1.PathTypePrefix),
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

func mustInitUnauthorizedErrorIngress() {
	clientset := util.MustInitK8sClientSet()

	// Try to delete the ingress if it already exists. Returning error is okay given it may not exist.
	clientset.NetworkingV1().Ingresses(ingressNamespace).Delete(context.Background(), ingressNameForUnauthorizedAccess, metav1.DeleteOptions{})

	if apiToken == "" {
		return
	}

	albstr := "alb"

	annotation := NewAnnotation()
	// TODO: when we have ingress sharding, we must pass in one of the lds in that group.
	annotation.SetGroup(deploymentIngressGroupName(nil), GroupOrderUnauthorized)
	annotation.SetDeploymentConditions(serviceNameForUnauthorizedDeployment, "*")
	annotation.SetActions(serviceNameForUnauthorizedAPIServer, unauthorizedAction)
	annotation.SetActions(serviceNameForUnauthorizedDeployment, unauthorizedAction)

	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:        ingressNameForUnauthorizedAccess,
			Namespace:   ingressNamespace,
			Annotations: annotation.Get(),
		},
		Spec: networkingv1.IngressSpec{
			IngressClassName: &albstr,
			Rules: []networkingv1.IngressRule{
				{
					IngressRuleValue: networkingv1.IngressRuleValue{
						HTTP: &networkingv1.HTTPIngressRuleValue{
							Paths: []networkingv1.HTTPIngressPath{
								newActionIngressPathPrefix(serviceNameForUnauthorizedDeployment, "/"),
								newActionIngressPathPrefix(serviceNameForUnauthorizedAPIServer, "/api/"),
							},
						},
					},
				},
			},
		},
	}

	// Update api-server Ingress
	result, err := clientset.NetworkingV1().Ingresses(ingressNamespace).Create(context.Background(), ingress, metav1.CreateOptions{})
	if err != nil {
		panic(err)
	}

	fmt.Printf("Created Ingress %q.\n", result.GetObjectMeta().GetName())
}
