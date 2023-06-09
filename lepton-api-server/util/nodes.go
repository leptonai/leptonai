package util

import (
	"context"
	"fmt"
	"strconv"

	corev1 "k8s.io/api/core/v1"
)

const (
	NvidiaGPUTypeLabel  = "nvidia.com/gpu.product"
	NvidiaGPUCountLabel = "nvidia.com/gpu.count"
)

func GetAccelerators() (map[string]int, error) {
	nodes := &corev1.NodeList{}
	if err := K8sClient.List(context.Background(), nodes); err != nil {
		return nil, fmt.Errorf("error retrieving node list: %v", err)
	}

	accelerators := make(map[string]int)

	for _, node := range nodes.Items {
		atype := node.Labels[NvidiaGPUTypeLabel]
		if len(atype) == 0 {
			continue
		}
		anum, err := strconv.Atoi(node.Labels[NvidiaGPUCountLabel])
		if err != nil {
			continue
		}

		if accelerators[atype] < anum {
			accelerators[atype] = anum
		}
	}

	return accelerators, nil
}

type MaxAllocatableSize struct {
	Core   float64 `json:"core"`
	Memory int64   `json:"memory"`
}

func GetMaxAllocatableSize() (*MaxAllocatableSize, error) {
	nodes := &corev1.NodeList{}
	if err := K8sClient.List(context.Background(), nodes); err != nil {
		return nil, fmt.Errorf("error retrieving node list: %v", err)
	}

	var maxAllocatableSize MaxAllocatableSize
	for _, node := range nodes.Items {
		cpu := node.Status.Allocatable.Cpu().AsApproximateFloat64()
		if cpu > maxAllocatableSize.Core {
			maxAllocatableSize.Core = cpu
		}

		mem, ok := node.Status.Allocatable.Memory().AsInt64()
		if !ok {
			// Todo: handle this error
			continue
		}

		memInMiB := mem / 1024 / 1024
		if memInMiB > maxAllocatableSize.Memory {
			maxAllocatableSize.Memory = memInMiB
		}
	}

	return &maxAllocatableSize, nil
}
