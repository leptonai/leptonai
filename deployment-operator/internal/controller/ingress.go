package controller

import (
	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	domainname "github.com/leptonai/lepton/go-pkg/domain-name"
	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	"github.com/leptonai/lepton/go-pkg/k8s/service"

	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

type Ingress struct {
	leptonDeployment *leptonaiv1alpha1.LeptonDeployment
}

// temporarily set ALB timeout to 5 minutes since some inference requests would take longer time when the service is busy 
const albTimeoutSec = 300

func newIngress(ld *leptonaiv1alpha1.LeptonDeployment) *Ingress {
	return &Ingress{
		leptonDeployment: ld,
	}
}

func (k *Ingress) createHostBasedDeploymentIngress(or []metav1.OwnerReference) *networkingv1.Ingress {
	ld := k.leptonDeployment
	domain := domainname.New(ld.Spec.WorkspaceName, ld.Spec.RootDomain)

	// Do not create host based ingress if rootDomain is not set.
	if len(ld.Spec.RootDomain) == 0 {
		return nil
	}

	annotation := ingress.NewAnnotation(domain.GetDeployment(ld.GetSpecName()), k.leptonDeployment.Spec.CertificateARN, albTimeoutSec)
	annotation.SetGroup(ingress.IngressGroupNameDeployment(ld.Namespace), ingress.IngressGroupOrderDeployment)
	annotation.SetAPITokenConditions(service.ServiceName(ld.GetSpecName()), k.leptonDeployment.GetTokens())
	annotation.SetDomainNameAndSSLCert()
	paths := ingress.NewPrefixPaths().AddServicePath(service.ServiceName(ld.GetSpecName()), service.Port, service.RootPath)
	return ingress.NewIngress(ingress.IngressNameForHostBased(ld.GetSpecName()), k.leptonDeployment.Namespace, domain.GetDeployment(ld.GetSpecName()), annotation.Get(), paths.Get(), or)
}

func (k *Ingress) createHeaderBasedDeploymentIngress(or []metav1.OwnerReference) *networkingv1.Ingress {
	ld := k.leptonDeployment

	annotation := ingress.NewAnnotation(ld.Spec.RootDomain, k.leptonDeployment.Spec.CertificateARN, albTimeoutSec)
	annotation.SetGroup(ingress.IngressGroupNameControlPlane(ld.Namespace), ingress.IngressGroupOrderDeployment)
	annotation.SetDeploymentAndAPITokenConditions(service.ServiceName(ld.GetSpecName()), ld.GetSpecName(), k.leptonDeployment.GetTokens())
	paths := ingress.NewPrefixPaths().AddServicePath(service.ServiceName(ld.GetSpecName()), service.Port, service.RootPath)
	return ingress.NewIngress(ingress.IngressNameForHeaderBased(ld.GetSpecName()), ld.Namespace, "", annotation.Get(), paths.Get(), or)
}
