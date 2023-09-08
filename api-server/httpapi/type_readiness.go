package httpapi

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	eventsv1 "k8s.io/api/events/v1"
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
	ReadinessReasonReady       ReplicaReadinessReason = "Ready"
	ReadinessReasonInProgress  ReplicaReadinessReason = "InProgress"
	ReadinessReasonNoCapacity  ReplicaReadinessReason = "NoCapacity"
	ReadinessReasonConfigError ReplicaReadinessReason = "ConfigError"
	ReadinessReasonSystemError ReplicaReadinessReason = "SystemError"
	ReadinessReasonUnknown     ReplicaReadinessReason = "Unknown"
)

func getDeploymentReadinessIssue(ctx context.Context, deployment *appsv1.Deployment) (DeploymentReadinessIssue, error) {
	podList := &corev1.PodList{}
	listOpts := []client.ListOption{
		client.InNamespace(deployment.Namespace),
		client.MatchingLabels(deployment.Spec.Selector.MatchLabels),
	}
	if err := k8s.MustLoadDefaultClient().List(ctx, podList, listOpts...); err != nil {
		return nil, fmt.Errorf("failed to list replicas: %w", err)
	}

	issue := make(DeploymentReadinessIssue)
	for _, pod := range podList.Items {
		if pod.Status.Phase != corev1.PodRunning && pod.Status.Phase != corev1.PodPending {
			goutil.Logger.Infow("pod is not (running, pending), skipping",
				"operation", "getDeploymentReadinessIssue",
				"pod", pod.Name,
				"phase", pod.Status.Phase,
				"reason", pod.Status.Reason,
			)
			continue
		}
		issue[ReplicaID(pod.Name)] = []ReplicaReadinessIssue{getReplicaReadinessIssue(ctx, &pod)}
	}
	return issue, nil
}

func getReplicaReadinessIssue(ctx context.Context, pod *corev1.Pod) ReplicaReadinessIssue {
	conditions := pod.Status.Conditions

	podReady := getConditionByType(conditions, corev1.PodReady)
	if podReady != nil && podReady.Status == corev1.ConditionTrue {
		return ReplicaReadinessIssue{ReadinessReasonReady, ""}
	}

	events, err := k8s.ListPodEvents(ctx, pod.Namespace, pod.Name)
	if err != nil || events == nil && events.Items == nil {
		goutil.Logger.Errorw("failed to list pod events",
			"operation", "getReplicaReadinessIssue",
			"pod", pod.Name,
			"err", err,
		)
		return ReplicaReadinessIssue{ReadinessReasonUnknown, err.Error()}
	}

	scheduled := getConditionByType(conditions, corev1.PodScheduled)
	if scheduled != nil && scheduled.Status == corev1.ConditionFalse {
		// some special handling for the scheduling failure
		// if we ever have a failed scheduling event, we should have a triggeredScaleUp event
		// 	if we see triggeredScaleUp, then we are adding capacity for the replica
		// 	if we see both triggeredScaleUp and notTriggerScaleUp, then we actually finished
		// 	adding capacity for the replica but waiting for the taint to be applied on the node.

		failedScheduleEvent := getLastEvent(events.Items, "", "FailedScheduling", "")
		triggeredScaleUp := getLastEvent(events.Items, "", "TriggeredScaleUp", "")
		notTriggerScaleUp := getLastEvent(events.Items, "", "NotTriggerScaleUp", "")
		if failedScheduleEvent != nil {
			if triggeredScaleUp != nil {
				return ReplicaReadinessIssue{ReadinessReasonInProgress, "Adding capacity for the replica"}
			}
			if notTriggerScaleUp != nil {
				return ReplicaReadinessIssue{ReadinessReasonNoCapacity, "Waiting to add capacity for the replica"}
			}
			return ReplicaReadinessIssue{ReadinessReasonNoCapacity, "Waiting to add capacity for the replica"}
		}
		return ReplicaReadinessIssue{ReadinessReasonNoCapacity, "Scheduling the replica"}
	}

	initialized := getConditionByType(conditions, corev1.PodInitialized)
	if initialized != nil && initialized.Status == corev1.ConditionFalse {
		readiness := getReadinessIssueFromEvents(events.Items)
		if readiness.Reason == ReadinessReasonInProgress {
			return ReplicaReadinessIssue{ReadinessReasonInProgress, "Initializing the replica"}
		}
		return readiness
	}

	containersReady := getConditionByType(conditions, corev1.ContainersReady)
	if containersReady != nil && containersReady.Status == corev1.ConditionFalse {
		return getReadinessIssueFromEvents(events.Items)
	}

	disruptionTarget := getConditionByType(conditions, corev1.DisruptionTarget)
	if disruptionTarget != nil && disruptionTarget.Status == corev1.ConditionTrue {
		return ReplicaReadinessIssue{ReadinessReasonInProgress, "the replica is about to be terminated due to a	disruption (such as preemption, eviction API or garbage-collection)"}
	}

	return getReadinessIssueFromEvents(events.Items)
}

func getConditionByType(conditions []corev1.PodCondition, conditionType corev1.PodConditionType) *corev1.PodCondition {
	for _, condition := range conditions {
		if condition.Type == conditionType {
			return &condition
		}
	}
	return nil
}

func getReadinessIssueFromEvents(events []eventsv1.Event) ReplicaReadinessIssue {
	// If the last event is normal, then we are still in progress.
	if lastEvent := getLastEvent(events, "", "", ""); lastEvent != nil && lastEvent.Type == "Normal" {
		switch lastEvent.Reason {
		case "Pulling":
			return ReplicaReadinessIssue{ReadinessReasonInProgress, "Pulling image"}
		case "Pulled":
			return ReplicaReadinessIssue{ReadinessReasonInProgress, "Creating the replica"}
		case "Created":
			return ReplicaReadinessIssue{ReadinessReasonInProgress, "Starting the replica"}
		case "Started":
			return ReplicaReadinessIssue{ReadinessReasonInProgress, "Waiting for the replica to become ready"}
		}
		return ReplicaReadinessIssue{ReadinessReasonInProgress, ""}
	}

	// parse the known warning events
	if lastEvent := getLastEvent(events, "Warning", "Failed", "Failed to pull image \"amazon/aws-cli\""); lastEvent != nil {
		if strings.Contains(lastEvent.Note, "401 Unauthorized") {
			return ReplicaReadinessIssue{ReadinessReasonConfigError, "Failed to pull image due to invalid dockerhub credentials"}
		}
		return ReplicaReadinessIssue{ReadinessReasonSystemError, "Failed to pull system image"}
	}
	if lastEvent := getLastEvent(events, "Warning", "Failed", "Failed to pull image"); lastEvent != nil {
		return ReplicaReadinessIssue{ReadinessReasonConfigError, "Failed to pull image: not found"}
	}
	if lastEvent := getLastEvent(events, "Warning", "Failed", "Error: couldn't find key non-exist in Secret"); lastEvent != nil {
		return ReplicaReadinessIssue{ReadinessReasonConfigError, "Secret not found"}
	}
	if lastEvent := getLastEvent(events, "Warning", "FailedMount", ""); lastEvent != nil {
		return ReplicaReadinessIssue{ReadinessReasonConfigError, "Mount point not found"}
	}
	if lastEvent := getLastEvent(events, "Warning", "Unhealthy", "Readiness probe failed"); lastEvent != nil {
		return ReplicaReadinessIssue{ReadinessReasonInProgress, goutil.MaskIPAddressInReadinessProbeMessage(lastEvent.Note)}
	}
	if lastEvent := getLastEvent(events, "Warning", "", ""); lastEvent != nil {
		return ReplicaReadinessIssue{ReadinessReasonUnknown, ""}
	}
	return ReplicaReadinessIssue{ReadinessReasonUnknown, ""}
}

func getLastEvent(events []eventsv1.Event, eventType, eventReason, eventNotePrefix string) *eventsv1.Event {
	var lastEvent *eventsv1.Event
	for i, event := range events {
		if (eventType == "" || event.Type == eventType) &&
			(eventReason == "" || event.Reason == eventReason) &&
			(eventNotePrefix == "" || strings.HasPrefix(event.Note, eventNotePrefix)) &&
			(lastEvent == nil || getEventLastObservedTime(&event).After(getEventLastObservedTime(lastEvent))) {
			lastEvent = &events[i]
		}
	}
	return lastEvent
}

func getEventLastObservedTime(event *eventsv1.Event) time.Time {
	lastObservedTime := event.EventTime.Time
	if lastObservedTime.IsZero() {
		lastObservedTime = event.DeprecatedLastTimestamp.Time
	}
	return lastObservedTime
}
