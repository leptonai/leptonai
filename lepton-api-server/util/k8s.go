package util

import (
	"os"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

func MustInitK8sClientSetWithConfig() (*kubernetes.Clientset, *rest.Config) {
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

func MustInitK8sClientSet() *kubernetes.Clientset {
	c, _ := MustInitK8sClientSetWithConfig()
	return c
}

func MustInitK8sDynamicClient() *dynamic.DynamicClient {
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

func GetOwnerRefFromUnstructured(u *unstructured.Unstructured) metav1.OwnerReference {
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

func ToContainerEnv(envs []leptonaiv1alpha1.EnvVar) []corev1.EnvVar {
	cenvs := make([]corev1.EnvVar, 0, len(envs))
	for _, env := range envs {
		cenvs = append(cenvs, corev1.EnvVar{
			Name:  env.Name,
			Value: env.Value,
		})
	}

	return cenvs
}
