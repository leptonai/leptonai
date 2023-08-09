package workspace

import (
	"testing"

	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"
)

func TestEFSMountTarget(t *testing.T) {
	privateSubnets := []string{"subnet-12345678", "subnet-87654321"}
	efsMountTargets := efsMountTargets(privateSubnets)

	expected := `{"az-0"={"subnet_id"="subnet-12345678"},"az-1"={"subnet_id"="subnet-87654321"}}`

	if efsMountTargets != expected {
		t.Errorf("expecting %s, got %s", expected, efsMountTargets)
	}
}

func TestValidateWorkspaceTier(t *testing.T) {
	tt := []struct {
		tier    string
		isValid bool
	}{
		{"basic", true},
		{"standard", true},
		{"enterprise", true},
		{"", true},
		{"invalid", false},
	}

	for _, tc := range tt {
		spec := crdv1alpha1.LeptonWorkspaceSpec{
			Tier: crdv1alpha1.LeptonWorkspaceTier(tc.tier),
		}
		err := validateTier(spec)
		if err != nil && tc.isValid {
			t.Errorf("expecting %s to be valid", tc.tier)
		}
		if err == nil && !tc.isValid {
			t.Errorf("expecting %s to be invalid", tc.tier)
		}
	}
}
