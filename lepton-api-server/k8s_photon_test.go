package main

import (
	"fmt"
	"testing"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	fake_dynamic "k8s.io/client-go/dynamic/fake"
)

func TestReadAllPhotonCR(t *testing.T) {
	scheme := runtime.NewScheme()
	schemeGroupVersion := schema.GroupVersion{Group: leptonAPIGroup, Version: photonAPIVersion}
	schemeBuilder := runtime.NewSchemeBuilder(func(scheme *runtime.Scheme) error {
		scheme.AddKnownTypes(schemeGroupVersion,
			&leptonaiv1alpha1.Photon{},
			&leptonaiv1alpha1.PhotonList{},
		)
		metav1.AddToGroupVersion(scheme, schemeGroupVersion)
		return nil
	})
	schemeBuilder.AddToScheme(scheme)

	list := generatePhotonList(photonNamespace, 10)

	// TODO(fix): pass &list itself
	// currently, panic with
	// *unstructured.Unstructured is not a list: no Items field in this object
	dynamicClient := fake_dynamic.NewSimpleDynamicClient(scheme, &list.Items[0])
	l, err := ReadAllPhotonCR(dynamicClient)
	if err != nil {
		t.Fatal(err)
	}
	if len(l) != 1 {
		t.Fatalf("expected 1 photon CR, but got %d", len(l))
	}
}

func generatePhotonList(namespace string, n int) leptonaiv1alpha1.PhotonList {
	items := make([]leptonaiv1alpha1.Photon, n)
	for i := 0; i < n; i++ {
		items[i] = leptonaiv1alpha1.Photon{
			TypeMeta: metav1.TypeMeta{},
			ObjectMeta: metav1.ObjectMeta{
				Namespace: namespace,
			},
			Spec: leptonaiv1alpha1.PhotonSpec{
				PhotonUserSpec: leptonaiv1alpha1.PhotonUserSpec{
					Name: fmt.Sprint(i),
				},
			},
			Status: leptonaiv1alpha1.PhotonStatus{},
		}
	}
	return leptonaiv1alpha1.PhotonList{
		TypeMeta: metav1.TypeMeta{},
		ListMeta: metav1.ListMeta{},
		Items:    items,
	}
}
