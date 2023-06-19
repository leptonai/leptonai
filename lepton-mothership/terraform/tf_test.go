package terraform

import (
	"testing"

	"github.com/leptonai/lepton/go-pkg/util"
)

func TestWorkspace(t *testing.T) {
	// Move to test main
	MustInit()
	testWorkspaceName := "test-workspace-" + util.RandString(6)

	err := CreateWorkspace(testWorkspaceName)
	if err != nil {
		t.Fatal(err)
	}

	l, err := ListWorkspaces()
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, w := range l.Items {
		if w.Name == testWorkspaceName {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("workspace %s not found", testWorkspaceName)
	}

	if err := IsWorkspaceEmpty(testWorkspaceName); err != nil {
		t.Fatal("workspace should be empty")
	}

	err = DeleteWorkspace(testWorkspaceName)
	if err != nil {
		t.Fatal(err)
	}
}
