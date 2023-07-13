package httpapi

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

type DeploymentReadinessIssue map[ReplicaID][]ReplicaReadinessIssue
type ReplicaID string
type ReplicaReadinessIssue struct {
	Reason  ReplicaReadinessReason `json:"reason"`
	Message string                 `json:"message"`
}
type ReplicaReadinessReason string

const (
	ReadinessReasonReady         ReplicaReadinessReason = "Ready"
	ReadinessReasonInProgress    ReplicaReadinessReason = "InProgress"
	ReadinessReasonNoCapacity    ReplicaReadinessReason = "NoCapacity"
	ReadinessReasonUserCodeError ReplicaReadinessReason = "UserCodeError"
	ReadinessReasonSystemError   ReplicaReadinessReason = "SystemError"
	ReadinessReasonUnknown       ReplicaReadinessReason = "Unknown"
)

func getDeploymentReadinessIssue(deployment *appsv1.Deployment) (DeploymentReadinessIssue, error) {
	podList := &corev1.PodList{}
	listOpts := []client.ListOption{
		client.InNamespace(deployment.Namespace),
		client.MatchingLabels(deployment.Spec.Selector.MatchLabels),
	}
	if err := k8s.Client.List(context.Background(), podList, listOpts...); err != nil {
		return nil, fmt.Errorf("failed to list replicas: %w", err)
	}

	issue := make(DeploymentReadinessIssue)
	for _, pod := range podList.Items {
		if pod.Status.Phase != corev1.PodRunning && pod.Status.Phase != corev1.PodPending {
			goutil.Logger.Warnw("pod is not (running, pending), skipping",
				"operation", "getDeploymentReadinessIssue",
				"pod", pod.Name,
				"phase", pod.Status.Phase,
				"reason", pod.Status.Reason,
			)
			continue
		}
		issue[ReplicaID(pod.Name)] = []ReplicaReadinessIssue{getReplicaReadinessIssue(&pod)}
	}
	return issue, nil
}

func getReplicaReadinessIssue(pod *corev1.Pod) ReplicaReadinessIssue {
	for _, containerStatus := range pod.Status.InitContainerStatuses {
		waiting := containerStatus.State.Waiting
		if waiting == nil {
			continue
		}
		switch waiting.Reason {
		case "ContainerCreating", "PodInitializing":
			return ReplicaReadinessIssue{Reason: ReadinessReasonInProgress, Message: fmt.Sprintf("initialization: %s", waiting.Message)}
		case "CrashLoopBackOff", "Error":
			return ReplicaReadinessIssue{Reason: ReadinessReasonSystemError, Message: fmt.Sprintf("initialization: %s", waiting.Message)}
		case "ErrImagePull", "ImagePullBackOff", "InvalidImageName":
			return ReplicaReadinessIssue{Reason: ReadinessReasonSystemError, Message: fmt.Sprintf("initialization: %s", waiting.Message)}
		case "CreateContainerError", "CreateContainerConfigError":
			return ReplicaReadinessIssue{Reason: ReadinessReasonSystemError, Message: fmt.Sprintf("initialization: %s", waiting.Message)}

		}
	}

	for _, containerStatus := range pod.Status.InitContainerStatuses {
		terminated := containerStatus.State.Terminated
		if terminated == nil {
			continue
		}
		switch terminated.Reason {
		case "OOMKilled", "Error", "ContainerCannotRun", "DeadlineExceeded":
			return ReplicaReadinessIssue{Reason: ReadinessReasonSystemError, Message: fmt.Sprintf("initialization: %s", terminated.Message)}
		}
	}

	for _, containerStatus := range pod.Status.ContainerStatuses {
		waiting := containerStatus.State.Waiting
		if waiting == nil {
			continue
		}
		switch waiting.Reason {
		case "ContainerCreating", "PodInitializing":
			return ReplicaReadinessIssue{Reason: ReadinessReasonInProgress, Message: waiting.Message}
		case "CrashLoopBackOff", "Error":
			return ReplicaReadinessIssue{Reason: ReadinessReasonUserCodeError, Message: waiting.Message}
		case "ErrImagePull", "ImagePullBackOff", "InvalidImageName":
			return ReplicaReadinessIssue{Reason: ReadinessReasonSystemError, Message: waiting.Message}
		case "CreateContainerError", "CreateContainerConfigError":
			return ReplicaReadinessIssue{Reason: ReadinessReasonSystemError, Message: waiting.Message}
		}
	}

	switch pod.Status.Phase {
	case corev1.PodPending:
		events, err := k8s.ListPodEvents(pod.Namespace, pod.Name)
		if err != nil {
			return ReplicaReadinessIssue{Reason: ReadinessReasonSystemError, Message: err.Error()}
		}
		for _, event := range events.Items {
			if event.Reason == "TriggeredScaleUp" {
				return ReplicaReadinessIssue{Reason: ReadinessReasonInProgress, Message: "Waiting to assign the replica to a machine"}
			}
		}
		return ReplicaReadinessIssue{Reason: ReadinessReasonNoCapacity, Message: "Waiting for more capacity"}
	case corev1.PodRunning:
		return ReplicaReadinessIssue{Reason: ReadinessReasonReady}
	default:
		return ReplicaReadinessIssue{Reason: ReadinessReasonUnknown, Message: fmt.Sprintf("Replica phase: %s, reason %s, message %s", pod.Status.Phase, pod.Status.Reason, pod.Status.Message)}
	}
}
