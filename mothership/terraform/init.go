package terraform

import (
	"context"
	"fmt"
	"time"

	"github.com/hashicorp/go-tfe"
	goutil "github.com/leptonai/lepton/go-pkg/util"
)

var (
	orgName = "lepton"
	// TODO: update me
	TempToken = "cna5nv2diSDDNA.atlasv1.ft1ccF2wpsvvFtT6fMSl7UEUQExeLhnxZneSQkyBUU7pCIVcYJqgGLTbdywX3OUlweE"
	client    *tfe.Client
)

const (
	defaultOperationTimeout = 10 * time.Second
)

func MustInit() {
	config := &tfe.Config{
		Token:             TempToken,
		RetryServerErrors: true,
	}
	var err error
	client, err = tfe.NewClient(config)
	if err != nil {
		goutil.Logger.Fatalw("failed to initialize Terraform client",
			"error", err,
		)
	}
}

// ListWorkspaces lists all workspaces.
func ListWorkspaces(ctx context.Context) (*tfe.WorkspaceList, error) {
	ctx, cancel := context.WithTimeout(ctx, defaultOperationTimeout)
	defer cancel()

	listOpt := tfe.WorkspaceListOptions{}
	return client.Workspaces.List(ctx, orgName, &listOpt)
}

// GetWorkspace gets a workspace.
func GetWorkspace(ctx context.Context, name string) (*tfe.Workspace, error) {
	ctx, cancel := context.WithTimeout(ctx, defaultOperationTimeout)
	defer cancel()

	return client.Workspaces.Read(ctx, orgName, name)
}

// CreateWorkspace creates a workspace.
func CreateWorkspace(ctx context.Context, name string) error {
	localExecution := "local"
	autoApply := true
	createOpt := tfe.WorkspaceCreateOptions{
		Name:          &name,
		AutoApply:     &autoApply,
		ExecutionMode: &localExecution,
	}

	ctx, cancel := context.WithTimeout(ctx, defaultOperationTimeout)
	defer cancel()

	workspace, err := client.Workspaces.Create(ctx, orgName, createOpt)
	if err != nil {
		return fmt.Errorf("failed to create workspace: %s", err)
	}

	goutil.Logger.Infow("Workspace created",
		"terraformWorkspace", workspace.Name,
		"terraformWorkspaceID", workspace.ID,
	)

	return nil
}

// DeleteEmptyWorkspace deletes a workspace if it is empty.
func DeleteEmptyWorkspace(ctx context.Context, name string) error {
	if err := IsWorkspaceEmpty(ctx, name); err != nil {
		return err
	}
	return DeleteWorkspace(ctx, name)
}

// DeleteWorkspace deletes a workspace.
func DeleteWorkspace(ctx context.Context, name string) error {
	ctx, cancel := context.WithTimeout(ctx, defaultOperationTimeout)
	defer cancel()

	return client.Workspaces.Delete(ctx, orgName, name)
}

// IsWorkspaceEmpty returns an error if the workspace is not empty.
func IsWorkspaceEmpty(ctx context.Context, name string) error {
	w, err := GetWorkspace(ctx, name)
	if err != nil {
		return err
	}
	if w.ResourceCount > 0 {
		return fmt.Errorf("workspace %s is not empty", name)
	}
	return nil
}

// ForceUnlockWorkspace unlocks a workspace that is locked by a run.
func ForceUnlockWorkspace(ctx context.Context, name string) error {
	ctx, cancel := context.WithTimeout(ctx, defaultOperationTimeout)
	defer cancel()

	w, err := client.Workspaces.Read(ctx, orgName, name)
	if err != nil {
		return err
	}
	_, err = client.Workspaces.ForceUnlock(ctx, w.ID)
	return err
}
