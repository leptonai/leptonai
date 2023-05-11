// TODO: use kubebuilder instead

package main

import (
	"context"
	"encoding/json"
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
)

var leptonAPIGroup = "lepton.ai"

var (
	photonKind       = "Photon"
	photonAPIVersion = "v1alpha1"
	photonResource   = "photons"
	photonNamespace  = "default"
)

func ReadAllPhotonCR() ([]*Photon, error) {
	dynamicClient := mustInitK8sDynamicClient()

	// Get the custom resource definition
	crdResource := schema.GroupVersionResource{
		Group:    leptonAPIGroup,
		Version:  photonAPIVersion,
		Resource: photonResource,
	}
	crd, err := dynamicClient.Resource(crdResource).Namespace(photonNamespace).List(
		context.TODO(),
		metav1.ListOptions{},
	)
	if err != nil {
		return nil, err
	}

	// Iterate over the custom resources
	var metadataList []*Photon
	for _, cr := range crd.Items {
		spec := cr.Object["spec"].(map[string]interface{})
		specStr, err := json.Marshal(spec)
		if err != nil {
			return nil, err
		}
		metadata := &Photon{}
		json.Unmarshal(specStr, &metadata)

		metadataList = append(metadataList, metadata)
	}

	return metadataList, nil
}

func DeletePhotonCR(metadata *Photon) error {
	dynamicClient := mustInitK8sDynamicClient()

	// Delete the custom resource object in Kubernetes
	crdResource := schema.GroupVersionResource{
		Group:    leptonAPIGroup,
		Version:  photonAPIVersion,
		Resource: photonResource,
	}
	err := dynamicClient.Resource(crdResource).Namespace(photonNamespace).Delete(
		context.TODO(),
		joinNameByDash(metadata.Name, metadata.ID),
		metav1.DeleteOptions{},
	)
	if err != nil {
		return err
	}

	return nil
}

func CreatePhotonCR(metadata *Photon) error {
	dynamicClient := mustInitK8sDynamicClient()

	// Define the custom resource object to create
	crd := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": leptonAPIGroup + "/" + photonAPIVersion,
			"kind":       photonKind,
			"metadata": map[string]interface{}{
				"name": joinNameByDash(metadata.Name, metadata.ID),
			},
			"spec": metadata,
		},
	}

	// Create the custom resource object in Kubernetes
	crdResource := schema.GroupVersionResource{
		Group:    leptonAPIGroup,
		Version:  photonAPIVersion,
		Resource: photonResource,
	}
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
