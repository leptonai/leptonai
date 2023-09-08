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

func createTestBaseSpec() crdv1alpha1.LeptonWorkspaceSpec {
	return crdv1alpha1.LeptonWorkspaceSpec{
		LBType:    "dedicated",
		State:     "normal",
		OwnerType: "customer",
		Name:      "goodname",
		Tier:      "basic",
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
		spec := createTestBaseSpec()
		spec.Tier = crdv1alpha1.LeptonWorkspaceTier(tc.tier)

		err := validateSpec(spec)
		if err != nil && tc.isValid {
			t.Errorf("expecting %s to be valid %s", tc.tier, err)
		}
		if err == nil && !tc.isValid {
			t.Errorf("expecting %s to be invalid", tc.tier)
		}
	}
}

func TestValidateLBType(t *testing.T) {
	tt := []struct {
		lbType  string
		isValid bool
	}{
		{"shared", true},
		{"dedicated", true},
		{"", false},
		{"invalid", false},
	}

	for _, tc := range tt {
		spec := createTestBaseSpec()
		spec.LBType = crdv1alpha1.LeptonWorkspaceLBType(tc.lbType)
		err := validateSpec(spec)
		if err != nil && tc.isValid {
			t.Errorf("expecting %s to be valid, %s", tc.lbType, err)
		}
		if err == nil && !tc.isValid {
			t.Errorf("expecting %s to be invalid", tc.lbType)
		}
	}
}

func TestValidateSpec(t *testing.T) {
	tt := []struct {
		state   string
		isValid bool
	}{
		{"normal", true},
		{"paused", true},
		{"", false},
		{"invalid", false},
		{"terminated", true},
	}

	for _, tc := range tt {
		spec := createTestBaseSpec()
		spec.State = crdv1alpha1.LeptonWorkspaceState(tc.state)
		err := validateSpec(spec)
		if err != nil && tc.isValid {
			t.Errorf("expecting %s to be valid: %s", tc.state, err)
		}
		if err == nil && !tc.isValid {
			t.Errorf("expecting %s to be invalid", tc.state)
		}
	}
}

func TestOwnerType(t *testing.T) {
	tt := []struct {
		ownerType string
		isValid   bool
	}{
		{"customer", true},
		{"sys", true},
		{"", false},
		{"invalid", false},
	}

	for _, tc := range tt {
		spec := createTestBaseSpec()
		spec.OwnerType = crdv1alpha1.LeptonWorkspaceOwnerType(tc.ownerType)
		err := validateSpec(spec)
		if err != nil && tc.isValid {
			t.Errorf("expecting %s to be valid: %s", tc.ownerType, err)
		}
		if err == nil && !tc.isValid {
			t.Errorf("expecting %s to be invalid", tc.ownerType)
		}
	}
}

func TestSpecName(t *testing.T) {
	tt := []struct {
		ownerType string
		name      string
		isValid   bool
	}{
		{"customer", "good", true},
		{"customer", "sysbad", false},
		{"customer", "badsys", false},
		{"customer", "leptongood", false},
		{"customer", "goodlepton", false},
		{"customer", "mothershipgood", false},
		{"customer", "goodmothership", false},
		{"customer", "goodmothershipgood", true},
		{"customer", "mothershigood", true},
		{"customer", "goodmothershi", true},
		{"sys", "good", true},
		{"sys", "sysbad", true},
		{"sys", "badsys", true},
		{"sys", "leptongood", false},
		{"sys", "goodlepton", false},
		{"sys", "mothershipgood", false},
		{"sys", "goodmothership", false},
		{"sys", "goodmothershipgood", true},
		{"sys", "mothershigood", true},
		{"sys", "goodmothershi", true},
	}
	for _, tc := range tt {
		spec := createTestBaseSpec()
		spec.OwnerType = crdv1alpha1.LeptonWorkspaceOwnerType(tc.ownerType)
		spec.Name = tc.name
		err := validateSpec(spec)
		if err != nil && tc.isValid {
			t.Errorf("expecting %s to be valid: %s", tc.name, err)
		}
		if err == nil && !tc.isValid {
			t.Errorf("expecting %s to be invalid", tc.name)
		}
	}
}
