package terraform

import (
	"testing"
)

func TestWorkspace(t *testing.T) {
	// Move to test main
	MustInit()
	testWorkspaceName := "test-workspace"

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

	err = DeleteWorkspace(testWorkspaceName)
	if err != nil {
		t.Fatal(err)
	}
}
