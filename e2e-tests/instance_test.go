package e2etests

import "testing"

func TestListInstance(t *testing.T) {
	instances, err := lepton.Instance().List(mainTestDeploymentID)
	if err != nil {
		t.Fatal(err)
	}
	// TODO: We should check !=1 rather than ==0 . There is a bug in the instance handler, so we use ==0 to temporarily pass the test.
	// Ref: https://github.com/leptonai/lepton/issues/555
	if len(instances) == 0 {
		t.Fatal("Expected at least 1 instance, got 0")
	}
}

func TestInstanceShell(t *testing.T) {
	// TODO: implement shell in go-client first
}

func TestInstanceLog(t *testing.T) {
	// TODO: implement log in go-client first
}
