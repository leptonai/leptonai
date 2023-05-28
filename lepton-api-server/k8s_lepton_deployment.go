package main

import (
	"context"
	"encoding/json"
	"fmt"

	leptonv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
)

var (
	leptonDeploymentKind       = "LeptonDeployment"
	leptonDeploymentAPIVersion = "v1alpha1"
	leptonDeploymentResource   = "leptondeployments"
	leptonDeploymentNamespace  = "default"
)

func CreateLeptonDeploymentCR(ld *LeptonDeployment) (*unstructured.Unstructured, error) {
	dynamicClient := mustInitK8sDynamicClient()

	crdResource := createCustomResourceObject()
	crd := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": leptonAPIGroup + "/" + leptonDeploymentAPIVersion,
			"kind":       leptonDeploymentKind,
			"metadata": map[string]interface{}{
				"name": joinNameByDash(ld.Name, ld.ID),
			},
			"spec": convertDeploymentToCr(ld),
		},
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

func DeleteLeptonDeploymentCR(ld *LeptonDeployment) error {
	dynamicClient := mustInitK8sDynamicClient()

	crdResource := createCustomResourceObject()
	err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).Delete(
		context.TODO(),
		joinNameByDash(ld.Name, ld.ID),
		metav1.DeleteOptions{},
	)
	if err != nil {
		return err
	}

	return nil
}

func ReadAllLeptonDeploymentCR() ([]*LeptonDeployment, error) {
	dynamicClient := mustInitK8sDynamicClient()

	crdResource := createCustomResourceObject()
	crd, err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).List(
		context.TODO(),
		metav1.ListOptions{},
	)
	if err != nil {
		return nil, err
	}

	// Convert the typed LeptonDeployment object into a LeptonDeployment object
	lds := []*LeptonDeployment{}
	for _, cr := range crd.Items {
		spec := cr.Object["spec"].(map[string]interface{})
		specStr, err := json.Marshal(spec)
		if err != nil {
			return nil, err
		}
		metadata := &leptonv1alpha1.LeptonDeploymentSpec{}
		json.Unmarshal(specStr, &metadata)

		lds = append(lds, convertCrToDeployment(metadata))
	}

	return lds, nil
}

func PatchLeptonDeploymentCR(ld *LeptonDeployment) (*unstructured.Unstructured, error) {
	dynamicClient := mustInitK8sDynamicClient()

	crdResource := createCustomResourceObject()

	cr, err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).Get(
		context.TODO(),
		joinNameByDash(ld.Name, ld.ID),
		metav1.GetOptions{},
	)
	if err != nil {
		return nil, err
	}

	cr.Object["spec"] = convertDeploymentToCr(ld)

	result, err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).Update(
		context.TODO(),
		cr,
		metav1.UpdateOptions{},
	)
	if err != nil {
		return nil, err
	}

	return result, nil
}

func createCustomResourceObject() schema.GroupVersionResource {
	crdResource := schema.GroupVersionResource{
		Group:    leptonAPIGroup,
		Version:  leptonDeploymentAPIVersion,
		Resource: leptonDeploymentResource,
	}
	return crdResource
}

func (ld *LeptonDeployment) validateDeploymentMetadata() error {
	if !validateName(ld.Name) {
		return fmt.Errorf("invalid name %s: %s", ld.Name, nameValidationMessage)
	}
	if ld.ResourceRequirement.CPU <= 0 {
		return fmt.Errorf("cpu must be positive")
	}
	if ld.ResourceRequirement.Memory <= 0 {
		return fmt.Errorf("memory must be positive")
	}
	if ld.ResourceRequirement.MinReplicas <= 0 {
		return fmt.Errorf("min replicas must be positive")
	}
	ph := photonDB.GetByID(ld.PhotonID)
	if ph == nil {
		return fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}
	return nil
}

func (ld *LeptonDeployment) validatePatchMetadata() error {
	valid := false
	if ld.ResourceRequirement.MinReplicas > 0 {
		valid = true
	}
	if ld.PhotonID != "" {
		ph := photonDB.GetByID(ld.PhotonID)
		if ph == nil {
			return fmt.Errorf("photon %s does not exist", ld.PhotonID)
		}
		valid = true
	}
	if !valid {
		return fmt.Errorf("no valid field to patch")
	}
	return nil
}
