// Package create implements create command.
package create

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	workspaceName string
	clusterName   string
	gitRef        string
	apiToken      string
	imageTag      string
	quotaGroup    string
	quotaCPU      int
	quotaMemory   int
	quotaGPU      int
	enableWeb     bool
	description   string
	tier          string
	lbType        string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership workspaces create" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "create",
		Short: "Create a workspace",
		Run:   createFunc,
	}
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "dev", "Name of the cluster to create the workspace in")
	cmd.PersistentFlags().StringVarP(&workspaceName, "workspace-name", "w", "", "Name of the workspace to create")
	cmd.PersistentFlags().StringVarP(&gitRef, "git-ref", "g", "main", "Git ref to use for the workspace")
	cmd.PersistentFlags().StringVarP(&apiToken, "api-token", "a", "", "API token to use for the workspace")
	cmd.PersistentFlags().StringVarP(&imageTag, "image-tag", "i", "", "Image tag to use for the workspace")
	cmd.PersistentFlags().StringVarP(&quotaGroup, "quota-group", "", "small", "Quota group for the workspace (small, medium, large, unlimited, custom)")
	cmd.PersistentFlags().IntVarP(&quotaCPU, "quota-cpu", "", 0, "Quota CPU for the workspace if quota group is custom")
	cmd.PersistentFlags().IntVarP(&quotaMemory, "quota-memory", "", 0, "Quota memory for the workspace if quota group is custom")
	cmd.PersistentFlags().IntVarP(&quotaGPU, "quota-gpu", "", 0, "Quota GPU for the workspace if quota group is custom")
	cmd.PersistentFlags().BoolVarP(&enableWeb, "enable-web", "e", false, "Enable web for the workspace")
	cmd.PersistentFlags().StringVarP(&description, "description", "d", "From cli for testing", "Description of the workspace")
	cmd.PersistentFlags().StringVarP(&tier, "tier", "", "basic", "Tier of the workspace")
	cmd.PersistentFlags().StringVarP(&lbType, "lb-type", "", string(crdv1alpha1.WorkspaceLBTypeDedicated), "If the deployments of workspace should use shared lb infra")
	return cmd
}

func createFunc(cmd *cobra.Command, args []string) {
	if clusterName == "" {
		log.Fatal("cluster name is required")
	}
	if workspaceName == "" {
		log.Fatal("workspace name is required")
	}
	if apiToken == "" {
		log.Println("[UNSAFE] api token is not provided")
	}

	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL

	workspace := crdv1alpha1.LeptonWorkspaceSpec{
		Name:        workspaceName,
		ClusterName: clusterName,
		GitRef:      gitRef,
		APIToken:    apiToken,
		ImageTag:    imageTag,
		QuotaGroup:  quotaGroup,
		EnableWeb:   enableWeb,
		State:       crdv1alpha1.WorkspaceStateNormal,
		Tier:        crdv1alpha1.LeptonWorkspaceTier(tier),
		LBType:      crdv1alpha1.LeptonWorkspaceLBType(lbType),

		Description: description,
	}

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
		workspace.QuotaCPU = quotaCPU
		workspace.QuotaMemoryInGi = quotaMemory
		workspace.QuotaGPU = quotaGPU
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
	}

	b, err := json.Marshal(workspace)
	if err != nil {
		log.Fatal("failed to marshal workspace spec: ", err)
	}

	cli := goclient.NewHTTP(mothershipURL, token)
	b, err = cli.RequestPath(http.MethodPost, "/workspaces", nil, b)
	if err != nil {
		log.Fatal("error sending request: ", err)
	}
	fmt.Printf("successfully sent %q: %s\n", http.MethodPost, string(b))
}
