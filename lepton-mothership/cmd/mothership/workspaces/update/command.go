// Package update implements update command.
package update

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/prompt"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	workspaceName string
	gitRef        string
	imageTag      string
	quotaGroup    string
	quotaCPU      int
	quotaMemory   int
	quotaGPU      int
	autoApprove   bool
	state         string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership workspaces update" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "update",
		Short: "update a workspace",
		Run:   updateFunc,
	}
	cmd.PersistentFlags().StringVarP(&workspaceName, "workspace-name", "w", "", "Name of the workspace to update")
	cmd.PersistentFlags().StringVarP(&gitRef, "git-ref", "g", "", "Git ref to use for the workspace terraform")
	cmd.PersistentFlags().StringVarP(&imageTag, "image-tag", "i", "", "Image tag to use for the workspace deployments")
	cmd.PersistentFlags().StringVarP(&state, "state", "", "", "Workspace running state (normal, paused, terminated)")
	cmd.PersistentFlags().StringVarP(&quotaGroup, "quota-group", "", "", "Quota group for the workspace (small, medium, large, unlimited, custom)")
	cmd.PersistentFlags().IntVarP(&quotaCPU, "quota-cpu", "", 0, "Quota CPU for the workspace if quota group is custom")
	cmd.PersistentFlags().IntVarP(&quotaMemory, "quota-memory", "", 0, "Quota memory in Gi for the workspace if quota group is custom")
	cmd.PersistentFlags().IntVarP(&quotaGPU, "quota-gpu", "", 0, "Quota GPU for the workspace if quota group is custom")
	cmd.PersistentFlags().BoolVar(&autoApprove, "auto-approve", false, "Set to auto-approve the action without prompt (if you know what you're doing)")
	return cmd
}

func updateFunc(cmd *cobra.Command, args []string) {
	if workspaceName == "" {
		log.Fatal("workspace name is required")
	}

	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL

	if !autoApprove {
		if !prompt.IsInputYes(fmt.Sprintf("Confirm to update a workspace %q via %q\n", workspaceName, mothershipURL)) {
			return
		}
	}

	// get the existing workspace
	cli := goclient.NewHTTP(mothershipURL, token)
	b, err := cli.RequestPath(http.MethodGet, "/workspaces/"+workspaceName, nil, nil)
	if err != nil {
		log.Fatal("error sending workspace get request: ", err)
	}
	workspace := crdv1alpha1.LeptonWorkspace{}
	err = json.Unmarshal(b, &workspace)
	if err != nil {
		log.Fatal("error unmarshalling workspace: ", err)
	}

	// update workspace spec
	updated := false
	workspaceSpec := workspace.Spec
	if gitRef != "" {
		workspaceSpec.GitRef = gitRef
		updated = true
	}
	if imageTag != "" {
		workspaceSpec.ImageTag = imageTag
		updated = true
	}
	if state != "" {
		workspaceSpec.State = crdv1alpha1.LeptonWorkspaceState(state)
		updated = true
	}
	if quotaGroup != "" {
		workspaceSpec.QuotaGroup = quotaGroup
		if quotaGroup == "custom" {
			if quotaCPU == 0 {
				log.Fatal("quota cpu is required when quota group is custom")
			}
			if quotaMemory == 0 {
				log.Fatal("quota memory is required when quota group is custom")
			}
			if quotaGPU == 0 {
				log.Fatal("quota gpu is required when quota group is custom")
			}
			workspaceSpec.QuotaCPU = quotaCPU
			workspaceSpec.QuotaMemoryInGi = quotaMemory
			workspaceSpec.QuotaGPU = quotaGPU
		} else {
			if quotaCPU != 0 {
				log.Fatal("quota cpu is not allowed when quota group is not custom")
			}
			if quotaMemory != 0 {
				log.Fatal("quota memory is not allowed when quota group is not custom")
			}
			if quotaGPU != 0 {
				log.Fatal("quota gpu is not allowed when quota group is not custom")
			}
			workspaceSpec.QuotaCPU = 0
			workspaceSpec.QuotaMemoryInGi = 0
			workspaceSpec.QuotaGPU = 0
		}
		updated = true
	}
	if !updated {
		log.Println("no updates to workspace spec")
		return
	}

	b, err = json.Marshal(workspaceSpec)
	if err != nil {
		log.Fatal("failed to marshal workspace spec: ", err)
	}
	log.Printf("updating workspace spec: %s", b)

	b, err = cli.RequestPath(http.MethodPatch, "/workspaces", nil, b)
	if err != nil {
		log.Fatal("error sending HTTP Patch request: ", err)
	}

	fmt.Printf("successfully sent %q: %s\n", http.MethodPatch, string(b))
}
