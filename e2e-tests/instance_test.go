package e2etests

import (
	"fmt"
	"testing"
	"time"
)

func TestListInstance(t *testing.T) {
	err := retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		instances, err := lepton.Instance().List(mainTestDeploymentID)
		if err != nil {
			t.Fatal(err)
		}
		if len(instances) != 1 {
			return fmt.Errorf("expected 1 instance, got %d", len(instances))
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestInstanceShell(t *testing.T) {
	err := retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		instances, err := lepton.Instance().List(mainTestDeploymentID)
		if err != nil {
			t.Fatal(err)
		}
		iid := instances[0].ID
		_, err = lepton.Instance().Shell(mainTestDeploymentID, iid)
		if err != nil {
			t.Fatal(err)
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestInstanceLog(t *testing.T) {
	// TODO: implement log in go-client first
}
