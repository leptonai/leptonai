// Package update implements update command.
package update

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/prompt"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	workspaceName string
	gitRef        string
	apiToken      string
	imageTag      string
	quotaGroup    string
	quotaCPU      int
	quotaMemory   int
	quotaGPU      int
	autoApprove   bool
	state         string
	tier          string
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
	cmd.PersistentFlags().StringVarP(&apiToken, "api-token", "a", "", "API token to use for the workspace")
	cmd.PersistentFlags().StringVarP(&imageTag, "image-tag", "i", "", "Image tag to use for the workspace deployments")
	cmd.PersistentFlags().StringVarP(&state, "state", "", "", "Workspace running state (normal, paused, terminated)")
	cmd.PersistentFlags().StringVarP(&quotaGroup, "quota-group", "", "", "Quota group for the workspace (small, medium, large, unlimited, custom)")
	cmd.PersistentFlags().IntVarP(&quotaCPU, "quota-cpu", "", 0, "Quota CPU for the workspace if quota group is custom")
	cmd.PersistentFlags().IntVarP(&quotaMemory, "quota-memory", "", 0, "Quota memory in Gi for the workspace if quota group is custom")
	cmd.PersistentFlags().IntVarP(&quotaGPU, "quota-gpu", "", 0, "Quota GPU for the workspace if quota group is custom")
	cmd.PersistentFlags().StringVarP(&tier, "tier", "", "", "Tier of the workspace")

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

	// update workspace spec
	spec := crdv1alpha1.LeptonWorkspaceSpec{}
	spec.Name = workspaceName
	if gitRef != "" {
		spec.GitRef = gitRef
	}
	if apiToken != "" {
		spec.APIToken = apiToken
	}
	if imageTag != "" {
		spec.ImageTag = imageTag
	}
	if state != "" {
		spec.State = crdv1alpha1.LeptonWorkspaceState(state)
	}
	if tier != "" {
		spec.Tier = crdv1alpha1.LeptonWorkspaceTier(tier)
	}
	if quotaGroup != "" {
		spec.QuotaGroup = quotaGroup
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
			spec.QuotaCPU = quotaCPU
			spec.QuotaMemoryInGi = quotaMemory
			spec.QuotaGPU = quotaGPU
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
			spec.QuotaCPU = 0
			spec.QuotaMemoryInGi = 0
			spec.QuotaGPU = 0
		}
	}

	b, err := json.Marshal(spec)
	if err != nil {
		log.Fatal("failed to marshal workspace spec: ", err)
	}
	log.Printf("updating workspace spec: %s", b)

	cli := goclient.NewHTTP(mothershipURL, token)
	b, err = cli.RequestPath(http.MethodPatch, "/workspaces", nil, b)
	if err != nil {
		log.Fatal("error sending HTTP Patch request: ", err)
	}

	fmt.Printf("successfully sent %q: %s\n", http.MethodPatch, string(b))
}
