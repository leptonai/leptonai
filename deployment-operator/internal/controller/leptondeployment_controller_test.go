package controller

import (
	"testing"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
)

func TestTransitionState(t *testing.T) {
	tests := []struct {
		replicas      int32
		readyReplicas int32
		state         leptonaiv1alpha1.LeptonDeploymentState
		expectedState leptonaiv1alpha1.LeptonDeploymentState
	}{
		{1, 1, "", "Running"},
		{1, 1, "Starting", "Running"},
		{1, 1, "Not Ready", "Running"},
		{1, 1, "Updating", "Running"},
		{1, 1, "Running", "Running"},

		{1, 0, "", "Starting"},
		{1, 0, "Starting", "Starting"},
		{1, 0, "Running", "Not Ready"},
		{1, 0, "Updating", "Not Ready"},
		{1, 0, "Not Ready", "Not Ready"},

		{2, 1, "", "Starting"},
		{2, 1, "Starting", "Starting"},
		{2, 1, "Running", "Updating"},
		{2, 1, "Updating", "Updating"},
		{2, 1, "Not Ready", "Updating"},
	}
	for _, test := range tests {
		state := transitionState(test.replicas, test.readyReplicas, test.state)
		if state != test.expectedState {
			t.Errorf("expected %s for %+v, got %s", test.expectedState, test, state)
		}
	}
}
