package terraform

import (
	"context"
	"fmt"
	"log"

	"github.com/hashicorp/go-tfe"
)

var (
	orgName = "lepton"
	// TODO: update me
	TempToken = "GkqbTdrOGe945A.atlasv1.GIhfprQqv3UJevUvB98zJrOVAPOzUbHyHVkyeTJPy9RhFBF1rV2TPvYFfUuV3pi5pK4"
	client    *tfe.Client
)

func MustInit() {
	config := &tfe.Config{
		Token:             TempToken,
		RetryServerErrors: true,
	}
	var err error
	client, err = tfe.NewClient(config)
	if err != nil {
		log.Fatal(err)
	}
}

// ListWorkspaces lists all workspaces.
func ListWorkspaces() (*tfe.WorkspaceList, error) {
	listOpt := tfe.WorkspaceListOptions{}
	return client.Workspaces.List(context.TODO(), orgName, &listOpt)
}

// GetWorkspace gets a workspace.
func GetWorkspace(name string) (*tfe.Workspace, error) {
	return client.Workspaces.Read(context.TODO(), orgName, name)
}

// CreateWorkspace creates a workspace.
func CreateWorkspace(name string) error {
	localExecution := "local"
	autoApply := true
	createOpt := tfe.WorkspaceCreateOptions{
		Name:          &name,
		AutoApply:     &autoApply,
		ExecutionMode: &localExecution,
	}

	workspace, err := client.Workspaces.Create(context.TODO(), orgName, createOpt)
	if err != nil {
		return fmt.Errorf("failed to create workspace: %s", err)
	}
	log.Printf("Workspace created: %s %s", workspace.Name, workspace.ID)

	return nil
}

// DeleteEmptyWorkspace deletes a workspace if it is empty.
func DeleteEmptyWorkspace(name string) error {
	if err := IsWorkspaceEmpty(name); err != nil {
		return err
	}
	return DeleteWorkspace(name)
}

// DeleteWorkspace deletes a workspace.
func DeleteWorkspace(name string) error {
	return client.Workspaces.Delete(context.TODO(), orgName, name)
}

// IsWorkspaceEmpty returns an error if the workspace is not empty.
func IsWorkspaceEmpty(name string) error {
	w, err := GetWorkspace(name)
	if err != nil {
		return err
	}
	if w.ResourceCount > 0 {
		return fmt.Errorf("workspace %s is not empty", name)
	}
	return nil
}

// ForceUnlockWorkspace unlocks a workspace that is locked by a run.
func ForceUnlockWorkspace(name string) error {
	w, err := client.Workspaces.Read(context.TODO(), orgName, name)
	if err != nil {
		return err
	}
	_, err = client.Workspaces.ForceUnlock(context.TODO(), w.ID)
	return err
}
