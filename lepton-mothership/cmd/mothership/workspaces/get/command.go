// Package get implements get command.
package get

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
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get a workspace Spec and Status",
		Run:   getFunc,
	}
	cmd.PersistentFlags().StringVarP(&workspaceName, "workspace-name", "w", "", "Name of the workspace to get")
	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
	token := common.ReadTokenFromFlag(cmd)
	mothershipURL := common.ReadMothershipURLFromFlag(cmd)

	if workspaceName == "" {
		log.Fatal("cluster name is required")
	}

	cli := goclient.NewHTTP(mothershipURL, token)
	b, err := cli.RequestPath(http.MethodGet, "/workspaces/"+workspaceName, nil, nil)
	if err != nil {
		log.Fatal("error sending request: ", err)
	}
	workspace := &crdv1alpha1.LeptonWorkspace{}
	if err := json.Unmarshal(b, &workspace); err != nil {
		log.Fatal("error unmarshalling response: ", err)
	}
	ret, err := json.MarshalIndent(workspace, "", "  ")
	if err != nil {
		log.Fatal("error marshalling response: ", err)
	}
	fmt.Println(string(ret))
}
