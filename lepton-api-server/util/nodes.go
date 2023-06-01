package util

import (
	"context"
	"fmt"
	"strconv"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const (
	NvidiaGPUTypeLabel  = "nvidia.com/gpu.product"
	NvidiaGPUCountLabel = "nvidia.com/gpu.count"
)

func GetAccelerators() (map[string]int, error) {
	clientset := MustInitK8sClientSet()

	accelerators := make(map[string]int)

	nodes, err := clientset.CoreV1().Nodes().List(context.Background(), metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("error retrieving node list: %v", err)
	}

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
	Core   float64
	Memory int64
}

func GetMaxAllocatableSize() (*MaxAllocatableSize, error) {
	clientset := MustInitK8sClientSet()

	nodes, err := clientset.CoreV1().Nodes().List(context.Background(), metav1.ListOptions{})
	if err != nil {
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
