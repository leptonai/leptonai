package quota

import (
	"testing"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	"k8s.io/utils/ptr"
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
				MinReplicas:   ptr.To[int32](12),
				ResourceShape: leptonaiv1alpha1.GP1Small,
			},
			o: nil,
			w: true,
		},
		// not enough CPU
		{
			q: cq,
			r: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   ptr.To[int32](13),
				ResourceShape: leptonaiv1alpha1.GP1Small,
			},
			o: nil,
			w: false,
		},
		// not enough GPU
		{
			q: cq,
			r: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   ptr.To[int32](1),
				ResourceShape: leptonaiv1alpha1.AC1T4,
			},
			o: nil,
			w: true,
		},
		{
			q: cq,
			r: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   ptr.To[int32](2),
				ResourceShape: leptonaiv1alpha1.AC1T4,
			},
			o: nil,
			w: false,
		},
		// not enough GPU if not release the resources used by the current deployment
		{
			q: cq,
			r: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   ptr.To[int32](2),
				ResourceShape: leptonaiv1alpha1.AC1T4,
			},
			o: &leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
				MinReplicas:   ptr.To[int32](1),
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

func TestGetTotalResource(t *testing.T) {
	rl := v1.ResourceList{
		v1.ResourceRequestsCPU:    resource.MustParse("12.6"),
		v1.ResourceRequestsMemory: resource.MustParse("48Gi"),
		"requests.nvidia.com/gpu": resource.MustParse("2.8"),
	}

	q := GetTotalResource(rl)

	if q.CPU != 12.6 {
		t.Errorf("CPU: %v, want %v", q.CPU, 12.6)
	}
	if q.Memory != 48*1024 {
		t.Errorf("Memory: %v, want %v", q.Memory, 48*1024)
	}
	if q.AcceleratorNum != 2.8 {
		t.Errorf("Ac: %v, want %v", q.AcceleratorNum, 2.8)
	}
}

func TestRemoveSystemLimitOverhead(t *testing.T) {
	rl := v1.ResourceList{
		v1.ResourceRequestsCPU:    resource.MustParse("17"),
		v1.ResourceRequestsMemory: resource.MustParse("65Gi"),
		"requests.nvidia.com/gpu": resource.MustParse("3"),
	}

	q := RemoveSystemLimitOverhead(GetTotalResource(rl))
	if q.CPU != 16 {
		t.Errorf("CPU: %v, want %v", q.CPU, 16)
	}
	if q.Memory != 64*1024 {
		t.Errorf("Memory: %v, want %v", q.Memory, 64*1024)
	}
	if q.AcceleratorNum != 3 {
		t.Errorf("Ac: %v, want %v", q.AcceleratorNum, 3)
	}
}

func TestRemoveSystemUsageOverhead(t *testing.T) {
	rl := v1.ResourceList{
		v1.ResourceRequestsCPU:    resource.MustParse("0"),
		v1.ResourceRequestsMemory: resource.MustParse("0"),
		"requests.nvidia.com/gpu": resource.MustParse("0"),
	}

	c := rl[v1.ResourceRequestsCPU]
	m := rl[v1.ResourceRequestsMemory]
	// for api server
	c.Add(resource.MustParse("50m"))
	m.Add(resource.MustParse("128Mi"))

	// for operator
	c.Add(resource.MustParse("100m"))
	m.Add(resource.MustParse("128Mi"))

	// for a cpu small
	c.Add(resource.MustParse("0.9"))
	m.Add(resource.MustParse("921.6Mi"))

	rl[v1.ResourceRequestsCPU] = c
	rl[v1.ResourceRequestsMemory] = m

	q := RemoveSystemUsageOverhead(GetTotalResource(rl))
	if q.CPU != 1 {
		t.Errorf("CPU: %v, want %v", q.CPU, 1)
	}
	if q.Memory != 1*1024 {
		t.Errorf("Memory: %v, want %v", q.Memory, 1*1024)
	}
	if q.AcceleratorNum != 0 {
		t.Errorf("Ac: %v, want %v", q.AcceleratorNum, 0)
	}
}
