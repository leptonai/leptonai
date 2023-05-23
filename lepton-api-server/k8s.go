package main

import (
	"os"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

func mustInitK8sClientSetWithConfig() (*kubernetes.Clientset, *rest.Config) {
	// Load Kubernetes configuration from default location or specified kubeconfig file
	config, err := clientcmd.BuildConfigFromFlags("", os.Getenv("KUBECONFIG"))
	if err != nil {
		panic(err)
	}

	// Create a Kubernetes client
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		panic(err)
	}

	return clientset, config
}

func mustInitK8sClientSet() *kubernetes.Clientset {
	c, _ := mustInitK8sClientSetWithConfig()
	return c
}

func mustInitK8sDynamicClient() *dynamic.DynamicClient {
	// Load Kubernetes configuration from default location or specified kubeconfig file
	config, err := clientcmd.BuildConfigFromFlags("", os.Getenv("KUBECONFIG"))
	if err != nil {
		panic(err)
	}

	// Create a dynamic client using the Kubernetes REST API
	dynamicClient, err := dynamic.NewForConfig(config)
	if err != nil {
		panic(err)
	}

	return dynamicClient
}

func getOwnerRefFromUnstructured(u *unstructured.Unstructured) metav1.OwnerReference {
	apiVersion := u.GetAPIVersion()
	kind := u.GetKind()
	name := u.GetName()
	uid := u.GetUID()

	return metav1.OwnerReference{
		APIVersion: apiVersion,
		Kind:       kind,
		Name:       name,
		UID:        uid,
	}
}
