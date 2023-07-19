package e2etests

import (
	"fmt"
	"testing"
	"time"
)

func TestDeploymentReadiness(t *testing.T) {
	err := retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		issue, err := lepton.Readiness().GetDeploymentReadinessIssue(mainTestDeploymentName)
		if err != nil {
			t.Fatal(err)
		}
		if len(issue) != 1 {
			return fmt.Errorf("expected 1 issue, got %d", len(issue))
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}
