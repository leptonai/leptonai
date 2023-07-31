package httpapi

import (
	"testing"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

func TestValidateCreateInput_ResourceRequirement(t *testing.T) {
	tests := []struct {
		r leptonaiv1alpha1.LeptonDeploymentResourceRequirement
		e bool
	}{
		{ // Good: Valid CPU and Memory
			leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				LeptonDeploymentReplicaResourceRequirement: leptonaiv1alpha1.LeptonDeploymentReplicaResourceRequirement{
					CPU:    1,
					Memory: 1024,
				},
			},
			false,
		},
		{ // Bad: Missing CPU
			leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				LeptonDeploymentReplicaResourceRequirement: leptonaiv1alpha1.LeptonDeploymentReplicaResourceRequirement{
					Memory: 1024,
				},
			},
			true,
		},
		{ // Bad: Missing Memory
			leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				LeptonDeploymentReplicaResourceRequirement: leptonaiv1alpha1.LeptonDeploymentReplicaResourceRequirement{
					CPU: 1,
				},
			},
			true,
		},
		{ // Bad: Missing CPU and Memory
			leptonaiv1alpha1.LeptonDeploymentResourceRequirement{},
			true,
		},
		{ // Good: Valid Shape
			leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				ResourceShape: leptonaiv1alpha1.GP1Small,
			},
			false,
		},
		{ // Good: Invalid Shape
			leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				ResourceShape: leptonaiv1alpha1.LeptonDeploymentResourceShape("invalid"),
			},
			true,
		},
		{ // Bad: both Shape and CPU and Memory
			leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				LeptonDeploymentReplicaResourceRequirement: leptonaiv1alpha1.LeptonDeploymentReplicaResourceRequirement{
					CPU:    1,
					Memory: 1024,
				},
				ResourceShape: leptonaiv1alpha1.GP1Small,
			},
			true,
		},
		{ // Bad: both Shape and CPU
			leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				LeptonDeploymentReplicaResourceRequirement: leptonaiv1alpha1.LeptonDeploymentReplicaResourceRequirement{
					CPU: 1,
				},
				ResourceShape: leptonaiv1alpha1.GP1Small,
			},
			true,
		},
		{ // Bad: both Shape and Memory
			leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				LeptonDeploymentReplicaResourceRequirement: leptonaiv1alpha1.LeptonDeploymentReplicaResourceRequirement{
					Memory: 1024,
				},
				ResourceShape: leptonaiv1alpha1.GP1Small,
			},
			true,
		},
	}

	h := &DeploymentHandler{}

	for i, tt := range tests {
		r := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
			Name:                "test",
			ResourceRequirement: tt.r,
		}
		r.ResourceRequirement.MinReplicas = 1
		err := h.validateCreateInput(&gin.Context{}, r)
		if tt.e && err == nil {
			t.Errorf("Test %d: Expected error, but got none", i)
		}
		if !tt.e && err != nil {
			t.Errorf("Test %d: Expected no error, but got %v", i, err)
		}
	}
}
