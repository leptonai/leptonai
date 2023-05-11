package main

import (
	"context"
	"encoding/json"
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/types"
)

var (
	leptonDeploymentKind       = "LeptonDeployment"
	leptonDeploymentAPIVersion = "v1alpha1"
	leptonDeploymentResource   = "leptondeployments"
	leptonDeploymentNamespace  = "default"
)

func CreateLeptonDeploymentCR(metadata *LeptonDeployment) (*unstructured.Unstructured, error) {
	dynamicClient := mustInitK8sDynamicClient()

	// Define the custom resource object to create
	crd := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": leptonAPIGroup + "/" + leptonDeploymentAPIVersion,
			"kind":       leptonDeploymentKind,
			"metadata": map[string]interface{}{
				"name": joinNameByDash(metadata.Name, metadata.ID),
			},
			"spec": *metadata,
		},
	}

	// Create the custom resource object in Kubernetes
	crdResource := schema.GroupVersionResource{
		Group:    leptonAPIGroup,
		Version:  leptonDeploymentAPIVersion,
		Resource: leptonDeploymentResource,
	}
	result, err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).Create(
		context.TODO(),
		crd,
		metav1.CreateOptions{},
	)
	if err != nil {
		return nil, err
	}

	// Print the response from Kubernetes
	fmt.Printf("Created Lepton Deployment CRD instance: %v\n", result)

	return result, nil
}

func DeleteLeptonDeploymentCR(metadata *LeptonDeployment) error {
	dynamicClient := mustInitK8sDynamicClient()

	// Delete the custom resource object in Kubernetes
	crdResource := schema.GroupVersionResource{
		Group:    leptonAPIGroup,
		Version:  leptonDeploymentAPIVersion,
		Resource: leptonDeploymentResource,
	}
	err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).Delete(
		context.TODO(),
		joinNameByDash(metadata.Name, metadata.ID),
		metav1.DeleteOptions{},
	)
	if err != nil {
		return err
	}

	return nil
}

func ReadAllLeptonDeploymentCR() ([]*LeptonDeployment, error) {
	dynamicClient := mustInitK8sDynamicClient()

	// List the custom resource object in Kubernetes
	crdResource := schema.GroupVersionResource{
		Group:    leptonAPIGroup,
		Version:  leptonDeploymentAPIVersion,
		Resource: leptonDeploymentResource,
	}
	crd, err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).List(
		context.TODO(),
		metav1.ListOptions{},
	)
	if err != nil {
		return nil, err
	}

	// Convert the typed LeptonDeployment object into a LeptonDeployment object
	metadataList := []*LeptonDeployment{}
	for _, cr := range crd.Items {
		spec := cr.Object["spec"].(map[string]interface{})
		specStr, err := json.Marshal(spec)
		if err != nil {
			return nil, err
		}
		metadata := &LeptonDeployment{}
		json.Unmarshal(specStr, &metadata)

		metadataList = append(metadataList, metadata)
	}

	return metadataList, nil
}

func PatchLeptonDeploymentCR(ld *LeptonDeployment) error {
	dynamicClient := mustInitK8sDynamicClient()

	// Patch the custom resource object in Kubernetes
	crdResource := schema.GroupVersionResource{
		Group:    leptonAPIGroup,
		Version:  leptonDeploymentAPIVersion,
		Resource: leptonDeploymentResource,
	}

	ldString, err := json.Marshal(ld)
	if err != nil {
		return err
	}

	_, err = dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).Patch(
		context.TODO(),
		joinNameByDash(ld.Name, ld.ID),
		types.MergePatchType,
		[]byte(fmt.Sprintf(`{"spec": %s}`, ldString)),
		metav1.PatchOptions{},
	)
	if err != nil {
		return err
	}

	return nil
}
