// TODO: use kubebuilder instead

package main

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/dynamic"
)

var leptonAPIGroup = "lepton.ai"

var (
	photonKind       = "Photon"
	photonAPIVersion = "v1alpha1"
	photonResource   = "photons"
	photonNamespace  = "default"
)

// Returns a default photon "schema.GroupVersionResource"
func createPhotonGVR() schema.GroupVersionResource {
	return schema.GroupVersionResource{
		Group:    leptonAPIGroup,
		Version:  photonAPIVersion,
		Resource: photonResource,
	}
}

func ReadAllPhotonCR(dynamicClient dynamic.Interface) ([]*leptonaiv1alpha1.Photon, error) {
	// Get the custom resource definition
	crdResource := createPhotonGVR()
	crd, err := dynamicClient.Resource(crdResource).Namespace(photonNamespace).List(
		context.TODO(),
		metav1.ListOptions{},
	)
	if err != nil {
		return nil, err
	}

	var phs []*leptonaiv1alpha1.Photon
	for _, cr := range crd.Items {
		ph := &leptonaiv1alpha1.Photon{}
		if err := runtime.DefaultUnstructuredConverter.FromUnstructured(cr.Object, ph); err != nil {
			return nil, err
		}
		phs = append(phs, ph)
	}

	return phs, nil
}

func ReadPhotonCR(name string) (*leptonaiv1alpha1.Photon, error) {
	dynamicClient := util.MustInitK8sDynamicClient()

	// Get the custom resource definition
	crdResource := createPhotonGVR()
	cr, err := dynamicClient.Resource(crdResource).Namespace(photonNamespace).Get(
		context.TODO(),
		name,
		metav1.GetOptions{},
	)
	if err != nil {
		return nil, err
	}

	ph := &leptonaiv1alpha1.Photon{}
	if err := runtime.DefaultUnstructuredConverter.FromUnstructured(cr.Object, ph); err != nil {
		return nil, err
	}

	return ph, nil
}

func DeletePhotonCR(ph *leptonaiv1alpha1.Photon) error {
	dynamicClient := util.MustInitK8sDynamicClient()

	// Delete the custom resource object in Kubernetes
	crdResource := createPhotonGVR()
	err := dynamicClient.Resource(crdResource).Namespace(photonNamespace).Delete(
		context.TODO(),
		ph.GetUniqName(),
		metav1.DeleteOptions{},
	)
	if err != nil {
		return err
	}

	return nil
}

func CreatePhotonCR(ph *leptonaiv1alpha1.Photon) error {
	dynamicClient := util.MustInitK8sDynamicClient()

	// Define the custom resource object to create
	crd := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": leptonAPIGroup + "/" + photonAPIVersion,
			"kind":       photonKind,
			"metadata": map[string]interface{}{
				"name":        ph.GetUniqName(),
				"annotations": ph.Annotations,
			},
			"spec": ph.Spec,
		},
	}

	// Create the custom resource object in Kubernetes
	crdResource := createPhotonGVR()
	result, err := dynamicClient.Resource(crdResource).Namespace(photonNamespace).Create(
		context.TODO(),
		crd,
		metav1.CreateOptions{},
	)
	if err != nil {
		return err
	}

	// Print the response from Kubernetes
	fmt.Printf("Created Photon CRD instance: %v\n", result)

	return nil
}
