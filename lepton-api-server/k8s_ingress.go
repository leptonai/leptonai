package main

import (
	"context"
	"log"

	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	"github.com/leptonai/lepton/go-pkg/k8s/service"

	networkingv1 "k8s.io/api/networking/v1"
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
	annotation := ingress.NewAnnotation(rootDomain, certificateARN)
	annotation.SetGroup(ingress.IngressGroupNameControlPlane(ingressNamespace), ingress.IngressGroupOrderAPIServer)
	if len(apiToken) > 0 {
		annotation.SetAPITokenConditions(service.ServiceName(deploymentNameAPIServer), []string{apiToken})
	}
	annotation.SetDomainNameAndSSLCert()
	paths := ingress.NewPrefixPaths().AddServicePath(service.ServiceName(deploymentNameAPIServer), apiServerPort, apiServerPath)
	ingress := ingress.NewIngress(ingress.IngressName(deploymentNameAPIServer), ingressNamespace, "", annotation.Get(), paths.Get(), nil)

	if err := k8s.Client.Update(context.Background(), ingress); err != nil {
		if !apierrors.IsNotFound(err) {
			log.Fatalln(err)
		}
		if err := k8s.Client.Create(context.Background(), ingress); err != nil {
			log.Fatalln(err)
		}
	}

	log.Printf("Created/updated Ingress %q.\n", ingress.Name)
}

func mustInitUnauthorizedErrorIngress() {
	// Try to delete the ingress if it already exists. Returning error is okay given it may not exist.
	k8s.Client.Delete(context.Background(), &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:      ingressNameForUnauthorizedAccess,
			Namespace: ingressNamespace,
		},
	})

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

	if err := k8s.Client.Update(context.Background(), ingress); err != nil {
		if !apierrors.IsNotFound(err) {
			log.Fatalln(err)
		}
		if err := k8s.Client.Create(context.Background(), ingress); err != nil {
			log.Fatalln(err)
		}
	}

	log.Printf("Created/updated Ingress %q.\n", ingress.Name)
}
