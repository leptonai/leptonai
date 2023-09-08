package e2etests

import "testing"

func TestEvent(t *testing.T) {
	events, err := lepton.Event().GetDeploymentEvents(mainTestDeploymentName)
	if err != nil {
		t.Fatalf("Error getting deployment events: %v", err)
	}
	if len(events) == 0 {
		t.Fatalf("Expected deployment to have at least one event, got %d", len(events))
	}
	for _, event := range events {
		if event.LastObservedTime.IsZero() {
			t.Fatalf("Expected LastObservedTime to not be zero")
		}
		if event.Count == 0 {
			t.Fatalf("Expected Count to not be zero")
		}
	}
}
