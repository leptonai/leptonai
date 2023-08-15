package httpapi

import (
	"context"
	"fmt"
	"log"
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
		failedScheduleEvent := getEventByReason(events.Items, "FailedScheduling")
		triggeredScaleUp := getEventByReason(events.Items, "TriggeredScaleUp")
		notTriggerScaleUp := getEventByReason(events.Items, "NotTriggerScaleUp")
		if failedScheduleEvent != nil {
			if triggeredScaleUp != nil {
				return ReplicaReadinessIssue{ReadinessReasonInProgress, "Adding capacity for the replica"}
			}
			if notTriggerScaleUp != nil {
				return ReplicaReadinessIssue{ReadinessReasonNoCapacity, "Waiting to add capacity for the replica"}
			}
			return ReplicaReadinessIssue{ReadinessReasonNoCapacity, failedScheduleEvent.Reason + ": " + failedScheduleEvent.Note}
		}
		return ReplicaReadinessIssue{ReadinessReasonNoCapacity, scheduled.Reason + ": " + scheduled.Message}
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

func getEventByReason(events []eventsv1.Event, reason string) *eventsv1.Event {
	for _, event := range events {
		if event.Reason == reason {
			return &event
		}
	}
	return nil
}

func getReadinessIssueFromEvents(events []eventsv1.Event) ReplicaReadinessIssue {
	event := findTheLastWarningEvent(events)
	if event != nil {
		return getReadinessIssueFromEvent(event)
	}
	event = findTheLastEvent(events)
	if event != nil {
		return getReadinessIssueFromEvent(event)
	}
	return ReplicaReadinessIssue{ReadinessReasonUnknown, ""}
}

func findTheLastWarningEvent(events []eventsv1.Event) *eventsv1.Event {
	var lastEvent *eventsv1.Event
	for i, event := range events {
		if event.Type == "Warning" &&
			(lastEvent == nil ||
				getEventLastObservedTime(&event).After(getEventLastObservedTime(lastEvent))) {
			lastEvent = &events[i]
		}
	}
	return lastEvent
}

func findTheLastEvent(events []eventsv1.Event) *eventsv1.Event {
	var lastEvent *eventsv1.Event
	for i, event := range events {
		if lastEvent == nil ||
			getEventLastObservedTime(&event).After(getEventLastObservedTime(lastEvent)) {
			lastEvent = &events[i]
			log.Printf("Last event: %s | %s | %s", lastEvent.Reason, lastEvent.Note, getEventLastObservedTime(lastEvent))
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

func getReadinessIssueFromEvent(event *eventsv1.Event) ReplicaReadinessIssue {
	message := fmt.Sprintf("%s:%s", event.Reason, event.Note)
	switch event.Type {
	case "Normal":
		return ReplicaReadinessIssue{ReadinessReasonInProgress, message}
	case "Warning":
		if strings.HasPrefix(event.Reason, "Fail") {
			// for example, FailMount, Failed (pulling image)
			return ReplicaReadinessIssue{ReadinessReasonConfigError, message}
		}
		return ReplicaReadinessIssue{ReadinessReasonInProgress, message}
	default:
		return ReplicaReadinessIssue{ReadinessReasonUnknown, message}
	}
}
