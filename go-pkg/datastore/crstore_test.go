package datastore

import (
	"context"
	"testing"

	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/util"
	mothershipv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func TestCRStore(t *testing.T) {
	// TODO split the test and work on more test cases
	namespace := util.RandString(8)
	nsObj := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: namespace,
		},
	}
	if err := k8s.Client.Create(context.Background(), nsObj); err != nil {
		t.Fatalf("Failed to create namespace %s: %v", namespace, err)
	}

	example := &mothershipv1alpha1.LeptonCluster{}
	s := NewCRStore[*mothershipv1alpha1.LeptonCluster](namespace, example)

	crName := util.RandString(6)
	// Create
	if err := s.Create(crName, example); err != nil {
		t.Fatalf("Failed to create: %v", err)
	}

	defer func() {
		if err := k8s.Client.Delete(context.Background(), nsObj); err != nil {
			t.Fatalf("Failed to delete namespace %s: %v", namespace, err)
		}
	}()
	// Get
	lc, err := s.Get(crName)
	if err != nil {
		t.Fatalf("Failed to get: %v", err)
	}
	if lc.GetName() != crName {
		t.Fatalf("Failed to get: %v", err)
	}
	// List
	lcs, err := s.List()
	if err != nil {
		t.Fatalf("Failed to list: %v", err)
	}
	found := false
	for _, lc := range lcs {
		if lc.GetName() == crName {
			found = true
		}
	}
	if !found {
		t.Fatalf("Expect to find %s in list, but not found", crName)
	}
	// Delete
	if err := s.Delete(crName); err != nil {
		t.Fatalf("Failed to delete: %v", err)
	}
}
