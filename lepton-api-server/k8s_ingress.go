package main

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

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

	emptyHostName = ""
)

const (
	GroupOrderDeployment   = 0
	GroupOrderAPIServer    = 900
	GroupOrderUnauthorized = 950
	// GroupOrderWeb is set in helm charts at /charts/template/web_ingress.yaml
	GroupOrderWeb = 1000
)

func deploymentHeaderBasedIngressName(ld *leptonaiv1alpha1.LeptonDeployment) string {
	return "ld-" + ld.GetName() + "-header-ingress"
}

func deploymentHostBasedIngressName(ld *leptonaiv1alpha1.LeptonDeployment) string {
	return "ld-" + ld.GetName() + "-host-ingress"
}

func deploymentIngressGroupName(ld *leptonaiv1alpha1.LeptonDeployment) string {
	// TODO: separate control plane and deployment ingress groups.
	// TOOD: shard deployments into multiple ingress groups because each
	// ALB can only support 100 rules thus 100 deployments per ingress.
	return controlPlaneIngressGroupName()
}

func controlPlaneIngressGroupName() string {
	return "lepton-" + ingressNamespace + "-control-plane"
}

func createDeploymentIngress(ld *leptonaiv1alpha1.LeptonDeployment, or metav1.OwnerReference) error {
	if err := createHeaderBasedDeploymentIngress(ld, or); err != nil {
		return err
	}
	if err := createHostBasedDeploymentIngress(ld, or); err != nil {
		return err
	}
	return nil
}

func createHostBasedDeploymentIngress(ld *leptonaiv1alpha1.LeptonDeployment, or metav1.OwnerReference) error {
	// Do not create host based ingress if rootDomain is not set.
	if len(rootDomain) == 0 {
		return nil
	}

	clientset := util.MustInitK8sClientSet()

	annotation := NewAnnotation()
	annotation.SetGroup(deploymentIngressGroupName(ld), GroupOrderDeployment)
	annotation.SetAPITokenConditions(serviceName(ld), apiToken)
	annotation.SetDomainNameAndSSLCert(fmt.Sprintf("%s.%s", ld.GetName(), rootDomain), certificateARN)
	paths := NewPrefixPaths().AddServicePath(serviceName(ld), servicePort, rootPath)
	ingress := newIngress(deploymentHostBasedIngressName(ld), ingressNamespace, util.DomainName(ld, rootDomain), annotation.Get(), paths.Get(), &or)

	result, err := clientset.NetworkingV1().Ingresses(ingressNamespace).Create(context.Background(), ingress, metav1.CreateOptions{})
	if err != nil {
		return err
	}
	fmt.Printf("Created Ingress %q.\n", result.GetObjectMeta().GetName())

	return nil
}

func createHeaderBasedDeploymentIngress(ld *leptonaiv1alpha1.LeptonDeployment, or metav1.OwnerReference) error {
	clientset := util.MustInitK8sClientSet()

	annotation := NewAnnotation()
	annotation.SetGroup(controlPlaneIngressGroupName(), GroupOrderDeployment)
	annotation.SetDeploymentAndAPITokenConditions(serviceName(ld), ld.GetName(), apiToken)
	paths := NewPrefixPaths().AddServicePath(serviceName(ld), servicePort, rootPath)
	ingress := newIngress(deploymentHeaderBasedIngressName(ld), ingressNamespace, emptyHostName, annotation.Get(), paths.Get(), &or)

	result, err := clientset.NetworkingV1().Ingresses(ingressNamespace).Create(context.Background(), ingress, metav1.CreateOptions{})
	if err != nil {
		return err
	}
	fmt.Printf("Created Ingress %q.\n", result.GetObjectMeta().GetName())

	return nil
}

func mustUpdateAPIServerIngress() {
	clientset := util.MustInitK8sClientSet()

	annotation := NewAnnotation()
	annotation.SetGroup(controlPlaneIngressGroupName(), GroupOrderAPIServer)
	annotation.SetAPITokenConditions(apiServerServiceName, apiToken)
	annotation.SetDomainNameAndSSLCert(rootDomain, certificateARN)
	paths := NewPrefixPaths().AddServicePath(apiServerServiceName, apiServerPort, apiServerPath)
	ingress := newIngress(apiServerIngressName, ingressNamespace, emptyHostName, annotation.Get(), paths.Get(), nil)

	result, err := clientset.NetworkingV1().Ingresses(ingressNamespace).
		Update(context.Background(), ingress, metav1.UpdateOptions{})
	if err != nil {
		panic(err)
	}

	fmt.Printf("Updated Ingress %q.\n", result.GetObjectMeta().GetName())
}

func mustInitUnauthorizedErrorIngress() {
	clientset := util.MustInitK8sClientSet()

	// Try to delete the ingress if it already exists. Returning error is okay given it may not exist.
	clientset.NetworkingV1().Ingresses(ingressNamespace).
		Delete(context.Background(), ingressNameForUnauthorizedAccess, metav1.DeleteOptions{})

	if apiToken == "" {
		return
	}

	annotation := NewAnnotation()
	// TODO: when we have ingress sharding, we must pass in one of the lds in that group.
	annotation.SetGroup(controlPlaneIngressGroupName(), GroupOrderUnauthorized)
	annotation.SetDeploymentConditions(serviceNameForUnauthorizedDeployment, "*")
	annotation.SetActions(serviceNameForUnauthorizedAPIServer, unauthorizedAction)
	annotation.SetActions(serviceNameForUnauthorizedDeployment, unauthorizedAction)
	paths := NewPrefixPaths()
	paths.AddAnnotationPath(serviceNameForUnauthorizedDeployment, rootPath)
	paths.AddAnnotationPath(serviceNameForUnauthorizedAPIServer, apiServerPath)
	ingress := newIngress(ingressNameForUnauthorizedAccess, ingressNamespace, emptyHostName, annotation.Get(), paths.Get(), nil)

	result, err := clientset.NetworkingV1().Ingresses(ingressNamespace).
		Create(context.Background(), ingress, metav1.CreateOptions{})
	if err != nil {
		panic(err)
	}

	fmt.Printf("Created Ingress %q.\n", result.GetObjectMeta().GetName())
}

func newIngress(name, namespace, hostName string, annotation map[string]string, paths []networkingv1.HTTPIngressPath, or *metav1.OwnerReference) *networkingv1.Ingress {
	albstr := "alb"
	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:        name,
			Namespace:   namespace,
			Annotations: annotation,
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
	if len(hostName) == 0 {
		ingress.Spec.Rules[0].Host = hostName
	}
	if or != nil {
		ingress.ObjectMeta.OwnerReferences = []metav1.OwnerReference{*or}
	}
	return ingress
}
