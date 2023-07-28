package datastore

import (
	"context"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const (
	testOperationTimeout = 60 * time.Second
)

func TestCRStore(t *testing.T) {
	// TODO split the test and work on more test cases
	namespace := "test-cr-" + util.RandString(8)
	nsObj := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: namespace,
		},
	}

	ctx, cancel := context.WithTimeout(context.Background(), testOperationTimeout)
	defer cancel()

	if err := k8s.Client.Create(ctx, nsObj); err != nil {
		t.Fatalf("Failed to create namespace %s: %v", namespace, err)
	}

	example := &leptonaiv1alpha1.Photon{}

	// TODO: enable backup in test
	s := NewCRStore[*leptonaiv1alpha1.Photon](namespace, example, nil)

	crName := "test-cr-" + util.RandString(6)

	// Create
	if err := s.Create(ctx, crName, example); err != nil {
		t.Fatalf("Failed to create: %v", err)
	}

	defer func() {
		if err := k8s.Client.Delete(ctx, nsObj); err != nil {
			t.Fatalf("Failed to delete namespace %s: %v", namespace, err)
		}
	}()
	// Get
	lc, err := s.Get(ctx, crName)
	if err != nil {
		t.Fatalf("Failed to get: %v", err)
	}
	if lc.GetName() != crName {
		t.Fatalf("Failed to get: %v", err)
	}
	// List
	lcs, err := s.List(ctx)
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

	err = s.Backup(ctx)
	if err != nil {
		t.Log("Failed to backup:", err)
	}

	if err := s.Delete(ctx, crName); err != nil {
		t.Fatalf("Failed to delete: %v", err)
	}
}
