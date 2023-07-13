// Package create implements create command.
package create

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	workspaceName string
	clusterName   string
	gitRef        string
	apiToken      string
	imageTag      string
	quotaGroup    string
	enableWeb     bool
	description   string
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
	cmd.PersistentFlags().StringVarP(&quotaGroup, "quota-group", "q", "small", "Quota group for the workspace")
	cmd.PersistentFlags().BoolVarP(&enableWeb, "enable-web", "e", false, "Enable web for the workspace")
	cmd.PersistentFlags().StringVarP(&description, "description", "d", "From cli for testing", "Description of the workspace")
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

	token := common.ReadTokenFromFlag(cmd)
	mothershipURL := common.ReadMothershipURLFromFlag(cmd)

	workspace := crdv1alpha1.LeptonWorkspaceSpec{
		Name:        workspaceName,
		ClusterName: clusterName,
		GitRef:      gitRef,
		APIToken:    apiToken,
		ImageTag:    imageTag,
		QuotaGroup:  quotaGroup,
		EnableWeb:   enableWeb,

		Description: description,
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
