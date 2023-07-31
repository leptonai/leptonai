package quota

import (
	"testing"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
)

func TestQuotaAdmit(t *testing.T) {
	cq := v1.ResourceQuota{
		Spec: v1.ResourceQuotaSpec{
			Hard: v1.ResourceList{
				v1.ResourceRequestsCPU:    resource.MustParse("12"),
				v1.ResourceRequestsMemory: resource.MustParse("48Gi"),
				"requests.nvidia.com/gpu": resource.MustParse("2"),
			},
		},
		Status: v1.ResourceQuotaStatus{
			Used: v1.ResourceList{
				v1.ResourceRequestsCPU:    resource.MustParse("1"),
				v1.ResourceRequestsMemory: resource.MustParse("4Gi"),
				"requests.nvidia.com/gpu": resource.MustParse("1"),
			},
		},
	}

	tests := []struct {
		q v1.ResourceQuota
		r *leptonaiv1alpha1.LeptonDeploymentResourceRequirement
		o *leptonaiv1alpha1.LeptonDeploymentResourceRequirement
		w bool
	}{
		{
			q: cq,
			r: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   12,
				ResourceShape: leptonaiv1alpha1.GP1Small,
			},
			o: nil,
			w: true,
		},
		// not enough CPU
		{
			q: cq,
			r: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   13,
				ResourceShape: leptonaiv1alpha1.GP1Small,
			},
			o: nil,
			w: false,
		},
		// not enough GPU
		{
			q: cq,
			r: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   1,
				ResourceShape: leptonaiv1alpha1.AC1T4,
			},
			o: nil,
			w: true,
		},
		{
			q: cq,
			r: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   2,
				ResourceShape: leptonaiv1alpha1.AC1T4,
			},
			o: nil,
			w: false,
		},
		// not enough GPU if not release the resources used by the current deployment
		{
			q: cq,
			r: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   2,
				ResourceShape: leptonaiv1alpha1.AC1T4,
			},
			o: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   1,
				ResourceShape: leptonaiv1alpha1.AC1T4,
			},
			w: true,
		},
	}

	for i, tt := range tests {
		if got := Admit(tt.q, tt.r, tt.o); got != tt.w {
			t.Errorf("%d: %v, want %v", i, got, tt.w)
		}
	}
}
