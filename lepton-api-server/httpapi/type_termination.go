package httpapi

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/go-pkg/k8s"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

type DeploymentTerminations map[ReplicaID][]ReplicaTermination

type ReplicaTermination struct {
	// Time at which previous execution of the replica started
	StartedAt int64 `json:"started_at"`
	// Time at which the replica last terminated
	FinisheddAt int64 `json:"finished_at"`
	// Exit code from the last termination of the replica
	ExitCode int32 `json:"exit_code"`
	// Brief Reason regarding the last termination of the replica
	Reason string `json:"reason"`
	// Message regarding the last termination of the replica
	Message string `json:"message"`
	// TODO: add the last few lines of the logs before termination
}

func getDeploymentTerminations(deployment *appsv1.Deployment) (DeploymentTerminations, error) {
	podList := &corev1.PodList{}
	listOpts := []client.ListOption{
		client.InNamespace(deployment.Namespace),
		client.MatchingLabels(deployment.Spec.Selector.MatchLabels),
	}
	if err := k8s.Client.List(context.Background(), podList, listOpts...); err != nil {
		return nil, fmt.Errorf("failed to list replicas: %w", err)
	}

	terminations := make(DeploymentTerminations)
	for _, pod := range podList.Items {
		// explictly not ignoring pods in Pending/Failed state
		ts := getReplicaTerminations(&pod)
		if len(ts) != 0 {
			terminations[ReplicaID(pod.Name)] = ts
		}
	}

	return terminations, nil
}

// getReplicaTerminations returns the termination information of all containers within a pod
func getReplicaTerminations(pod *corev1.Pod) []ReplicaTermination {
	terminations := make([]ReplicaTermination, 0)

	for _, containerStatus := range pod.Status.ContainerStatuses {
		if containerStatus.LastTerminationState.Terminated != nil {
			if containerStatus.State.Terminated.Reason == "Completed" {
				// ignore containers that completed successfully
				continue
			}
			rt := ReplicaTermination{
				StartedAt:   pod.Status.StartTime.Unix(),
				FinisheddAt: containerStatus.State.Terminated.FinishedAt.Unix(),
				ExitCode:    containerStatus.State.Terminated.ExitCode,
				Reason:      containerStatus.State.Terminated.Reason,
				Message:     containerStatus.State.Terminated.Message,
			}
			terminations = append(terminations, rt)
		}
	}

	return terminations
}
