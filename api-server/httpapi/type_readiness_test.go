package httpapi

import (
	"testing"

	corev1 "k8s.io/api/core/v1"
	eventsv1 "k8s.io/api/events/v1"
)

func TestGetConditionByType(t *testing.T) {
	conditions := []corev1.PodCondition{
		{
			Type:   corev1.PodScheduled,
			Status: corev1.ConditionTrue,
		},
		{
			Type:   corev1.PodInitialized,
			Status: corev1.ConditionTrue,
		},
		{
			Type:   corev1.PodReady,
			Status: corev1.ConditionTrue,
		},
		{
			Type:   corev1.ContainersReady,
			Status: corev1.ConditionFalse,
		},
		{
			Type:   corev1.DisruptionTarget,
			Status: corev1.ConditionTrue,
		},
	}
	for _, c := range conditions {
		status := getConditionByType(conditions, c.Type).Status
		if status != c.Status {
			t.Errorf("getConditionByType(%v) = %v, want %v", c.Type, status, c.Status)
		}
	}
}

func TestGetEventByReason(t *testing.T) {
	events := []eventsv1.Event{
		{
			Reason: "Normal",
			Note:   "Created pod: test",
		},
		{
			Reason: "Warning",
			Note:   "Failed to create pod: test",
		},
	}
	for _, e := range events {
		note := getEventByReason(events, e.Reason).Note
		if note != e.Note {
			t.Errorf("getEventByReason(%v) = %v, want %v", e.Reason, note, e.Note)
		}
	}
}
