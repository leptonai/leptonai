package datastore

import (
	"context"
	"testing"
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/util"

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

	if err := k8s.MustLoadDefaultClient().Create(ctx, nsObj); err != nil {
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
		if err := k8s.MustLoadDefaultClient().Delete(ctx, nsObj); err != nil {
			t.Fatalf("Failed to delete namespace %s: %v", namespace, err)
		}
	}()

	t.Run("TestCRStoreCreateConflict", func(t *testing.T) {
		if err := s.Create(ctx, crName, example); err == nil {
			t.Fatalf("Expect to fail with conflict, but not")
		}
	})

	t.Run("TestCRStoreUpdate", func(t *testing.T) {
		example.Spec.Image = "test-image"
		if err := s.Update(ctx, crName, example); err != nil {
			t.Fatalf("Failed to update: %v", err)
		}
		lc, err := s.Get(ctx, crName)
		if err != nil {
			t.Fatalf("Failed to get: %v", err)
		}
		if lc.Spec.Image != "test-image" {
			t.Fatalf("Failed to update: %v", err)
		}
	})

	t.Run("TestCRStoreUpdateNonExist", func(t *testing.T) {
		if err := s.Update(ctx, "non-exist", example); err == nil {
			t.Fatalf("Expect to fail with not found, but not")
		}
	})

	t.Run("TestCRStoreGet", func(t *testing.T) {
		lc, err := s.Get(ctx, crName)
		if err != nil {
			t.Fatalf("Failed to get: %v", err)
		}
		if lc.GetName() != crName {
			t.Fatalf("Failed to get: %v", err)
		}
	})

	t.Run("TestCRStoreList", func(t *testing.T) {
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
	})

	t.Run("TestCRStoreDeleteNonExist", func(t *testing.T) {
		if err := s.Delete(ctx, "non-exist"); err == nil {
			t.Fatalf("Expect to fail with not found, but not")
		}
	})

	t.Run("TestCRStoreBackup", func(t *testing.T) {
		err := s.Backup(ctx)
		if err != nil {
			t.Log("Failed to backup:", err)
		}
	})

	t.Run("TestCRStoreDelete", func(t *testing.T) {
		if err := s.Delete(ctx, crName); err != nil {
			t.Fatalf("Failed to delete: %v", err)
		}
		_, err := s.Get(ctx, crName)
		if err == nil {
			t.Fatalf("Expect to fail with not found, but not")
		}
	})
}
