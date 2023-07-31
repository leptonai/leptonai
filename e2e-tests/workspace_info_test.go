package e2etests

import "testing"

func TestWorkspaceInfo(t *testing.T) {
	info, err := lepton.Workspace().Info()
	if err != nil {
		t.Fatal(err)
	}
	if info.BuildTime == "" {
		t.Error("BuildTime is empty")
	}
	if info.GitCommit == "" {
		t.Error("GitCommit is empty")
	}
	if info.WorkspaceName == "" {
		t.Error("WorkspaceName is empty")
	}
	if info.ResourceQuota.Limit.CPU == 0 {
		t.Error("ResourceQuota.Limit is empty")
	}
	if info.ResourceQuota.Used.CPU == 0 {
		t.Error("ResourceQuota.Used is empty")
	}
}
