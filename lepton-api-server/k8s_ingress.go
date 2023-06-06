package main

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/lepton-api-server/util"

	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var (
	ingressNamespace = "default"
	certificateARN   = ""
	rootDomain       = ""
	apiToken         = ""
)

const (
	deploymentNameAPIServer = "lepton-api-server"

	serviceNameForUnauthorizedDeployment = "response-401-deployment"
	serviceNameForUnauthorizedAPIServer  = "response-401-apiserver"
	ingressNameForUnauthorizedAccess     = "response-401-ingress"

	unauthorizedAction = `{"type":"fixed-response","fixedResponseConfig":{"contentType":"text/plain","statusCode":"401","messageBody":"Not Authorized"}}`
)

func mustInitAPIServerIngress() {
	clientset := util.MustInitK8sClientSet()

	annotation := ingress.NewAnnotation(rootDomain, certificateARN)
	annotation.SetGroup(ingress.IngressGroupNameControlPlane(ingressNamespace), ingress.IngressGroupOrderAPIServer)
	if len(apiToken) > 0 {
		annotation.SetAPITokenConditions(service.ServiceName(deploymentNameAPIServer), []string{apiToken})
	}
	annotation.SetDomainNameAndSSLCert()
	paths := ingress.NewPrefixPaths().AddServicePath(service.ServiceName(deploymentNameAPIServer), apiServerPort, apiServerPath)
	ingress := ingress.NewIngress(ingress.IngressName(deploymentNameAPIServer), ingressNamespace, "", annotation.Get(), paths.Get(), nil)

	result, err := clientset.NetworkingV1().Ingresses(ingressNamespace).
		Update(context.Background(), ingress, metav1.UpdateOptions{})
	if err != nil {
		if !apierrors.IsNotFound(err) {
			panic(err)
		}
		result, err = clientset.NetworkingV1().Ingresses(ingressNamespace).
			Create(context.Background(), ingress, metav1.CreateOptions{})
		if err != nil {
			panic(err)
		}
	}

	fmt.Printf("Created/updated Ingress %q.\n", result.GetObjectMeta().GetName())
}

func mustInitUnauthorizedErrorIngress() {
	clientset := util.MustInitK8sClientSet()

	// Try to delete the ingress if it already exists. Returning error is okay given it may not exist.
	clientset.NetworkingV1().Ingresses(ingressNamespace).
		Delete(context.Background(), ingressNameForUnauthorizedAccess, metav1.DeleteOptions{})

	if len(apiToken) == 0 {
		return
	}

	annotation := ingress.NewAnnotation(rootDomain, certificateARN)
	// TODO: when we have ingress sharding, we must pass in one of the lds in that group.
	annotation.SetGroup(ingress.IngressGroupNameControlPlane(ingressNamespace), ingress.IngressGroupOrderUnauthorized)
	annotation.SetDeploymentConditions(serviceNameForUnauthorizedDeployment, "*")
	annotation.SetActions(serviceNameForUnauthorizedAPIServer, unauthorizedAction)
	annotation.SetActions(serviceNameForUnauthorizedDeployment, unauthorizedAction)
	paths := ingress.NewPrefixPaths()
	paths.AddAnnotationPath(serviceNameForUnauthorizedDeployment, rootPath)
	paths.AddAnnotationPath(serviceNameForUnauthorizedAPIServer, apiServerPath)
	ingress := ingress.NewIngress(ingressNameForUnauthorizedAccess, ingressNamespace, "", annotation.Get(), paths.Get(), nil)

	result, err := clientset.NetworkingV1().Ingresses(ingressNamespace).
		Update(context.Background(), ingress, metav1.UpdateOptions{})
	if err != nil {
		if !apierrors.IsNotFound(err) {
			panic(err)
		}
		result, err = clientset.NetworkingV1().Ingresses(ingressNamespace).
			Create(context.Background(), ingress, metav1.CreateOptions{})
		if err != nil {
			panic(err)
		}
	}

	fmt.Printf("Created/updated Ingress %q.\n", result.GetObjectMeta().GetName())
}
