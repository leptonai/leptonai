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

func TestGetEventBy(t *testing.T) {
	events := []eventsv1.Event{
		{
			Type:   "Normal",
			Reason: "Pulling",
			Note:   "Created pod: test",
		},
		{
			Type:   "Warning",
			Reason: "Pulled",
			Note:   "Failed to create pod: test",
		},
	}
	tests := []struct {
		Type        string
		Reason      string
		NotePrefix  string
		ExpectedNil bool
	}{
		{
			Type:        "Normal",
			Reason:      "Pulling",
			NotePrefix:  "Created",
			ExpectedNil: false,
		},
		{
			Type:        "Warning",
			Reason:      "Pulled",
			NotePrefix:  "Failed",
			ExpectedNil: false,
		},
		{
			Type:        "",
			Reason:      "Pulled",
			NotePrefix:  "Failed",
			ExpectedNil: false,
		},
		{
			Type:        "Normal",
			Reason:      "Pulling",
			NotePrefix:  "",
			ExpectedNil: false,
		},
		{
			Type:        "Warning",
			Reason:      "Pulled",
			NotePrefix:  "Created",
			ExpectedNil: true,
		},
	}
	for _, test := range tests {
		e := getLastEvent(events, test.Type, test.Reason, test.NotePrefix)
		if e == nil && !test.ExpectedNil {
			t.Errorf("getLastEventByTypeAndReasonAndNotePrefix(%v, %v, %v) = nil, want non-nil", test.Type, test.Reason, test.NotePrefix)
		}
		if e != nil && test.ExpectedNil {
			t.Errorf("getLastEventByTypeAndReasonAndNotePrefix(%v, %v, %v) != nil, want nil", test.Type, test.Reason, test.NotePrefix)
		}
	}
}
