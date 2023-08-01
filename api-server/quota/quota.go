package quota

// TODO: consider moving this to go-pkg/quota

import (
	"fmt"
	"math"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	"github.com/leptonai/lepton/go-pkg/deploymentutil"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"

	v1 "k8s.io/api/core/v1"
)

const (
	sysQuotaLimitOverheadCPU        = 1
	sysQuotaLimitOverheadMemoryInGi = 1
	sysQuotaLimitOverheadGPU        = 0

	operatorUsageOverheadCPU         = 0.1
	operatorUsageOverheadMemoryInGi  = 0.125
	apiServerUsageOverheadCPU        = 0.05
	apiServerUsageOverheadMemoryInGi = 0.125
)

// TotalResource is a list of aggergated resource for workspaces.
type TotalResource struct {
	// CPU is the total CPU quota in cores.
	CPU float64 `json:"cpu"`
	// Memory is the total memory quota in MiB.
	Memory int64 `json:"memory"`
	// AcceleratorNum is the total accelerator quota in number of cards.
	AcceleratorNum float64 `json:"accelerator_num"`
}

// Admit checks if a LeptonDeploymentResourceRequirement can be admitted to a ResourceQuota
// after release the resources used by the old deployment if any.
func Admit(q v1.ResourceQuota, r *leptonaiv1alpha1.LeptonDeploymentResourceRequirement, o *leptonaiv1alpha1.LeptonDeploymentResourceRequirement) bool {
	if o != nil { // release the resources used by the old deployment if any
		kc := deploymentutil.LeptonResourceToKubeResource(*o)
		for requestName, request := range kc.Requests {
			requestName = v1.ResourceName("requests." + requestName.String())
			_, ok := q.Spec.Hard[requestName]
			if !ok {
				// no limit set, continue
				continue
			}

			for i := 0; i < int(o.MinReplicas); i++ {
				// improve me: only release the resources actually conusmed by the old deployment
				// basically number of running pod...
				u := q.Status.Used[requestName]
				u.Sub(request)
				q.Status.Used[requestName] = u
			}
		}
	}

	kr := deploymentutil.LeptonResourceToKubeResource(*r)

	for requestName, request := range kr.Requests { // check if the new deployment can be admitted
		requestName = v1.ResourceName("requests." + requestName.String())

		h, ok := q.Spec.Hard[requestName]
		if !ok {
			// no limit set, continue
			continue
		}
		u := q.Status.Used[requestName]

		for i := 0; i < int(r.MinReplicas); i++ {
			u.Add(request)
		}

		if h.Cmp(u) < 0 {
			return false
		}
	}

	return true
}

// GetTotalResource converts Kubernetes Resource to TotalResource.
func GetTotalResource(ql v1.ResourceList) TotalResource {
	var (
		cpu            float64
		mem            int64
		acceleratorNum float64
	)

	if v, ok := ql[v1.ResourceRequestsCPU]; ok {
		// Keep 3 decimal places
		cpu = float64(v.MilliValue()) / 1000
	}
	if v, ok := ql[v1.ResourceRequestsMemory]; ok {
		// From Bytes to MiB
		mem = v.Value() / 1024 / 1024
	}
	if v, ok := ql["requests.nvidia.com/gpu"]; ok {
		// Keep 3 decimal places
		acceleratorNum = float64(v.MilliValue()) / 1000
	}

	q := TotalResource{
		CPU:            cpu,
		Memory:         mem,
		AcceleratorNum: acceleratorNum,
	}

	return q
}

// RemoveSystemLimitOverhead removes system limit overhead from the given quota.
func RemoveSystemLimitOverhead(q TotalResource) TotalResource {
	q.CPU -= sysQuotaLimitOverheadCPU
	q.Memory -= sysQuotaLimitOverheadMemoryInGi * 1024
	q.AcceleratorNum -= sysQuotaLimitOverheadGPU
	return q
}

// RemoveSystemUsageOverhead removes system usage overhead from the given quota.
func RemoveSystemUsageOverhead(q TotalResource) TotalResource {
	q.CPU -= (operatorUsageOverheadCPU + apiServerUsageOverheadCPU)
	q.Memory -= (operatorUsageOverheadMemoryInGi + apiServerUsageOverheadMemoryInGi) * 1024
	q.CPU = q.CPU / (1 - deploymentutil.RequestSysOverhead)
	q.Memory = int64(math.Ceil((float64(q.Memory) / (1 - deploymentutil.RequestSysOverhead))))
	return q
}

// SetResourceQuotaStatus sets the quota requirement for the given workspace spec.
func SetQuotaFromQuotaGroup(spec *crdv1alpha1.LeptonWorkspaceSpec) error {
	switch spec.QuotaGroup {
	case "small":
		spec.QuotaCPU = 16
		spec.QuotaMemoryInGi = 64
		spec.QuotaGPU = 1
	case "medium":
		spec.QuotaCPU = 64
		spec.QuotaMemoryInGi = 256
		spec.QuotaGPU = 4
	case "large":
		spec.QuotaCPU = 256
		spec.QuotaMemoryInGi = 1024
		spec.QuotaGPU = 16
	case "unlimited":
		spec.QuotaCPU = 0
		spec.QuotaMemoryInGi = 0
		spec.QuotaGPU = 0
	case "custom":
	default:
		return fmt.Errorf("invalid quota group %s", spec.QuotaGroup)
	}
	if spec.QuotaGroup != "unlimited" {
		spec.QuotaCPU += sysQuotaLimitOverheadCPU
		spec.QuotaMemoryInGi += sysQuotaLimitOverheadMemoryInGi
		spec.QuotaGPU += sysQuotaLimitOverheadGPU
	}
	return nil
}
