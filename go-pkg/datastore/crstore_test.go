package datastore

import (
	"testing"

	"github.com/leptonai/lepton/go-pkg/util"
	mothershipv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
)

func TestCRStore(t *testing.T) {
	// TODO split the test and work on more test cases
	namespace := "unit-test"
	example := &mothershipv1alpha1.LeptonCluster{}
	s := NewCRStore[*mothershipv1alpha1.LeptonCluster](namespace, example)

	name := util.RandString(6)

	lcs, err := s.List()
	if err != nil {
		t.Fatalf("Failed to list: %v", err)
	}
	if len(lcs) != 0 {
		t.Fatalf("Expected 0 item in list, got %d", len(lcs))
	}

	if err = s.Create(name, example); err != nil {
		t.Fatalf("Failed to create: %v", err)
	}

	defer func() {
		err := s.Delete(name)
		if err != nil {
			t.Fatalf("Failed to delete: %v", err)
		}
	}()

	lc, err := s.Get(name)
	if err != nil {
		t.Fatalf("Failed to get: %v", err)
	}
	if lc.GetName() != name {
		t.Fatalf("Failed to get: %v", err)
	}
	lcs, err = s.List()
	if err != nil {
		t.Fatalf("Failed to list: %v", err)
	}
	if len(lcs) != 1 {
		t.Fatalf("Expected 1 item in list, got %d", len(lcs))
	}
	if lcs[0].GetName() != name {
		t.Fatalf("Expected name %s, got %s", name, lcs[0].GetName())
	}
}
