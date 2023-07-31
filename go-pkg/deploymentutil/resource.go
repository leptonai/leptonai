package deploymentutil

import (
	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
)

const (
	nvidiaGPUResourceKey = "nvidia.com/gpu"
)

// LeptonResourceToKubeResource converts a LeptonDeploymentResourceRequirement to a corev1.ResourceRequirements
// TODO: add tests
func LeptonResourceToKubeResource(lr leptonaiv1alpha1.LeptonDeploymentResourceRequirement) corev1.ResourceRequirements {
	// we need to set request to a smaller value to account for shared node resources
	requestFactor := 0.9
	cpuValue := lr.CPU
	memValue := lr.Memory
	storageValue := lr.EphemeralStorageInGB

	if lr.ResourceShape != "" {
		replicaResourceRequirement, err := leptonaiv1alpha1.ShapeToReplicaResourceRequirement(lr.ResourceShape)
		if err != nil {
			goutil.Logger.Errorw("Unexpected shape to requirement error, using small shape resource requirement",
				"error", err,
			)
			replicaResourceRequirement, _ = leptonaiv1alpha1.ShapeToReplicaResourceRequirement(leptonaiv1alpha1.GP1Small)
		}

		cpuValue = replicaResourceRequirement.CPU
		memValue = replicaResourceRequirement.Memory
		storageValue = replicaResourceRequirement.EphemeralStorageInGB
	}

	cpuRequestQuantity := *resource.NewScaledQuantity(int64(cpuValue*requestFactor*1000), -3)
	cpuLimitQuantity := *resource.NewScaledQuantity(int64(cpuValue*1000), -3)
	memRequestQuantity := *resource.NewQuantity(int64(float64(memValue)*requestFactor)*1024*1024, resource.BinarySI)
	memLimitQuantity := *resource.NewQuantity(memValue*1024*1024, resource.BinarySI)

	// Define the main container
	resources := corev1.ResourceRequirements{
		Requests: corev1.ResourceList{
			corev1.ResourceCPU:    cpuRequestQuantity,
			corev1.ResourceMemory: memRequestQuantity,
		},
		Limits: corev1.ResourceList{
			corev1.ResourceCPU:    cpuLimitQuantity,
			corev1.ResourceMemory: memLimitQuantity,
		},
	}

	if storageValue != 0 {
		storageQuantity := *resource.NewQuantity(storageValue*1024*1024*1024, resource.BinarySI)
		resources.Requests[corev1.ResourceEphemeralStorage] = storageQuantity
		resources.Limits[corev1.ResourceEphemeralStorage] = storageQuantity
	}

	an, at := lr.GetAcceleratorRequirement()

	if at != "" && an > 0 {
		// if gpu is enabled, set gpu resource limit and node selector
		rv := *resource.NewQuantity(int64(an), resource.DecimalSI)
		resources.Limits[corev1.ResourceName(nvidiaGPUResourceKey)] = rv
		// cluster-autoscaler uses this key to prevent early scale-down on new/upcoming pods
		// even without this, execution uses the "resources.Limits" as defaults
		resources.Requests[corev1.ResourceName(nvidiaGPUResourceKey)] = rv
	}

	return resources
}
