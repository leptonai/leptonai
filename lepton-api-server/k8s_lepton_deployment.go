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
)

var (
	leptonDeploymentKind       = "LeptonDeployment"
	leptonDeploymentAPIVersion = "v1alpha1"
	leptonDeploymentResource   = "leptondeployments"
	leptonDeploymentNamespace  = "default"
)

func CreateLeptonDeploymentCR(ld *leptonaiv1alpha1.LeptonDeployment) (*unstructured.Unstructured, error) {
	dynamicClient := util.MustInitK8sDynamicClient()

	crdResource := createCustomResourceObject()
	crd := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": leptonAPIGroup + "/" + leptonDeploymentAPIVersion,
			"kind":       leptonDeploymentKind,
			"metadata": map[string]interface{}{
				"name":        ld.GetName(),
				"annotations": ld.Annotations,
			},
			"spec": ld.Spec,
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

func DeleteLeptonDeploymentCR(ld *leptonaiv1alpha1.LeptonDeployment) error {
	dynamicClient := util.MustInitK8sDynamicClient()

	crdResource := createCustomResourceObject()
	err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).Delete(
		context.TODO(),
		ld.GetName(),
		metav1.DeleteOptions{},
	)
	if err != nil {
		return err
	}

	return nil
}

func ReadAllLeptonDeploymentCR() ([]*leptonaiv1alpha1.LeptonDeployment, error) {
	dynamicClient := util.MustInitK8sDynamicClient()

	crdResource := createCustomResourceObject()
	crd, err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).List(
		context.TODO(),
		metav1.ListOptions{},
	)
	if err != nil {
		return nil, err
	}

	lds := []*leptonaiv1alpha1.LeptonDeployment{}
	for _, cr := range crd.Items {
		ld := &leptonaiv1alpha1.LeptonDeployment{}
		if err := runtime.DefaultUnstructuredConverter.FromUnstructured(cr.Object, ld); err != nil {
			return nil, err
		}
		lds = append(lds, ld)
	}

	return lds, nil
}

func ReadLeptonDeploymentCR(name string) (*leptonaiv1alpha1.LeptonDeployment, error) {
	dynamicClient := util.MustInitK8sDynamicClient()

	crdResource := createCustomResourceObject()
	cr, err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).Get(
		context.TODO(),
		name,
		metav1.GetOptions{},
	)
	if err != nil {
		return nil, err
	}

	ld := &leptonaiv1alpha1.LeptonDeployment{}
	if err := runtime.DefaultUnstructuredConverter.FromUnstructured(cr.Object, ld); err != nil {
		return nil, err
	}

	return ld, nil

}

func PatchLeptonDeploymentCR(ld *leptonaiv1alpha1.LeptonDeployment) (*unstructured.Unstructured, error) {
	dynamicClient := util.MustInitK8sDynamicClient()

	crdResource := createCustomResourceObject()

	cr, err := dynamicClient.Resource(crdResource).Namespace(leptonDeploymentNamespace).Get(
		context.TODO(),
		ld.GetName(),
		metav1.GetOptions{},
	)
	if err != nil {
		return nil, err
	}

	cr.Object["spec"] = ld.Spec

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
