package main

import (
	"context"
	"fmt"
	"strconv"

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

	headerKeyForLeptonDeploymentRouting = "deployment"

	serviceNameForUnauthorizedDeploymentAccess = "response-401-deployment"
	serviceNameForUnauthorizedAPIServerAccess  = "response-401-apiserver"
	ingressNameForUnauthorizedAccess           = "response-401-ingress"

	unauthorizedAction = `{"type":"fixed-response","fixedResponseConfig":{"contentType":"text/plain","statusCode":"401","messageBody":"Not Authorized"}}`
)

const (
	// GroupOrderDeployment is set via omitting the group.order annotation
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

func newDeploymentIngressAnnotation(ld *httpapi.LeptonDeployment) map[string]string {
	annotation := map[string]string{
		"alb.ingress.kubernetes.io/scheme":           "internet-facing",
		"alb.ingress.kubernetes.io/target-type":      "ip",
		"alb.ingress.kubernetes.io/healthcheck-path": "/healthz",
		"alb.ingress.kubernetes.io/group.name":       deploymentIngressGroupName(ld),
	}
	// Set required annotation for header based routing.
	key, value := newAnnotationKeyValueForHeaderBasedRouting(ld)
	if apiToken != "" {
		key, value = newAnnotationKeyValueForHeaderBasedRoutingWithAPIToken(ld)
	}
	annotation[key] = value
	// Set optional annotation for custom domain and SSL certificate.
	if rootDomain != "" {
		annotation["external-dns.alpha.kubernetes.io/hostname"] = ld.DomainName(rootDomain)
		if certificateARN != "" {
			annotation["alb.ingress.kubernetes.io/listen-ports"] = `[{"HTTPS":443}]`
			annotation["alb.ingress.kubernetes.io/certificate-arn"] = certificateARN
		}
	}
	return annotation
}

func newUnauthorizedIngressAnnotation() map[string]string {
	annotation := map[string]string{
		"alb.ingress.kubernetes.io/scheme":      "internet-facing",
		"alb.ingress.kubernetes.io/target-type": "ip",
		// TODO: when we have ingress sharding, we must pass in one of the lds in that group.
		"alb.ingress.kubernetes.io/group.name":  deploymentIngressGroupName(nil),
		"alb.ingress.kubernetes.io/group.order": strconv.Itoa(GroupOrderUnauthorized),
	}
	annotation["alb.ingress.kubernetes.io/actions."+serviceNameForUnauthorizedDeploymentAccess] = unauthorizedAction
	annotation["alb.ingress.kubernetes.io/actions."+serviceNameForUnauthorizedAPIServerAccess] = unauthorizedAction
	annotation["alb.ingress.kubernetes.io/conditions."+serviceNameForUnauthorizedDeploymentAccess] = fmt.Sprintf(`[{"field":"http-header","httpHeaderConfig":{"httpHeaderName":"%s","values":["%s"]}}]`, headerKeyForLeptonDeploymentRouting, "*")

	if rootDomain != "" && certificateARN != "" {
		annotation["alb.ingress.kubernetes.io/listen-ports"] = `[{"HTTPS":443}]`
	}
	return annotation
}

func newAPIServerIngressAnnotation() map[string]string {
	annotation := map[string]string{
		"alb.ingress.kubernetes.io/scheme":           "internet-facing",
		"alb.ingress.kubernetes.io/target-type":      "ip",
		"alb.ingress.kubernetes.io/healthcheck-path": "/healthz",
		"alb.ingress.kubernetes.io/group.name":       controlPlaneIngressGroupName(),
		"alb.ingress.kubernetes.io/group.order":      strconv.Itoa(GroupOrderAPIServer),
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
	annotations := newAPIServerIngressAnnotation()
	if apiToken != "" {
		key, value := newAnnotationKeyValueForAPIKey(apiServerServiceName)
		annotations[key] = value
	}

	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:        apiServerIngressName,
			Namespace:   ingressNamespace,
			Annotations: annotations,
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
	annotations := newUnauthorizedIngressAnnotation()

	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:        ingressNameForUnauthorizedAccess,
			Namespace:   ingressNamespace,
			Annotations: annotations,
		},
		Spec: networkingv1.IngressSpec{
			IngressClassName: &albstr,
			Rules: []networkingv1.IngressRule{
				{
					IngressRuleValue: networkingv1.IngressRuleValue{
						HTTP: &networkingv1.HTTPIngressRuleValue{
							Paths: []networkingv1.HTTPIngressPath{
								newActionIngressPathPrefix(serviceNameForUnauthorizedDeploymentAccess, "/"),
								newActionIngressPathPrefix(serviceNameForUnauthorizedAPIServerAccess, "/api/"),
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

func newAnnotationKeyValueForHeaderBasedRouting(ld *httpapi.LeptonDeployment) (key, value string) {
	key = "alb.ingress.kubernetes.io/conditions." + serviceName(ld)
	value = fmt.Sprintf(`[{"field":"http-header","httpHeaderConfig":{"httpHeaderName":"%s","values":["%s"]}}]`, headerKeyForLeptonDeploymentRouting, ld.Name)
	return
}

func newAnnotationKeyValueForAPIKey(serviceName string) (key, value string) {
	key = "alb.ingress.kubernetes.io/conditions." + serviceName
	value = fmt.Sprintf(`[{"field":"http-header","httpHeaderConfig":{"httpHeaderName":"Authorization","values":["Bearer %s"]}}]`, apiToken)
	return
}

func newAnnotationKeyValueForHeaderBasedRoutingWithAPIToken(ld *httpapi.LeptonDeployment) (key, value string) {
	key = "alb.ingress.kubernetes.io/conditions." + serviceName(ld)
	value = fmt.Sprintf(`[{"field":"http-header","httpHeaderConfig":{"httpHeaderName":"%s","values":["%s"]}}, {"field":"http-header","httpHeaderConfig":{"httpHeaderName":"Authorization","values":["Bearer %s"]}}]`, headerKeyForLeptonDeploymentRouting, ld.Name, apiToken)
	return
}
