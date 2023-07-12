package e2etests

import "testing"

func TestWorkspaceInfo(t *testing.T) {
	info, err := lepton.Workspace().Info()
	if err != nil {
		t.Fatal(err)
	}
	if info.BuildTime == "" {
		t.Fatal("BuildTime is empty")
	}
	if info.GitCommit == "" {
		t.Fatal("GitCommit is empty")
	}
	if info.WorkspaceName == "" {
		t.Fatal("WorkspaceName is empty")
	}
}
