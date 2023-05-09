package main

import (
	"context"
	"fmt"

	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var ingressNamespace = "default"

func ingressName(ld *LeptonDeployment) string {
	return ld.Name + "-ingress"
}

func createIngress(ld *LeptonDeployment, or metav1.OwnerReference) error {
	// Create a Kubernetes client
	clientset := mustInitK8sClientSet()

	albstr := "alb"
	pt := networkingv1.PathTypePrefix
	// Define Ingress object
	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:      ingressName(ld),
			Namespace: ingressNamespace,
			Annotations: map[string]string{
				"alb.ingress.kubernetes.io/scheme":      "internet-facing",
				"alb.ingress.kubernetes.io/target-type": "ip",
			},
			OwnerReferences: []metav1.OwnerReference{or},
		},
		Spec: networkingv1.IngressSpec{
			IngressClassName: &albstr,
			Rules: []networkingv1.IngressRule{
				{
					IngressRuleValue: networkingv1.IngressRuleValue{
						HTTP: &networkingv1.HTTPIngressRuleValue{
							Paths: []networkingv1.HTTPIngressPath{
								{
									Path:     "/",
									PathType: &pt,
									Backend: networkingv1.IngressBackend{
										Service: &networkingv1.IngressServiceBackend{
											Name: ld.Name + "-service",
											Port: networkingv1.ServiceBackendPort{
												Number: 8080,
											},
										},
									},
								},
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

func watchForIngressEndpoint(name string) (string, error) {
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
