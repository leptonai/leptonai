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

func ListWorkspaces() (*tfe.WorkspaceList, error) {
	listOpt := tfe.WorkspaceListOptions{}
	return client.Workspaces.List(context.TODO(), orgName, &listOpt)
}

func GetWorkspace(name string) (*tfe.Workspace, error) {
	return client.Workspaces.Read(context.TODO(), orgName, name)
}

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

func DeleteWorkspace(name string) error {
	return client.Workspaces.Delete(context.TODO(), orgName, name)
}
