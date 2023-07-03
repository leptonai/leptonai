// Package delete implements delete command.
package delete

import (
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"

	"github.com/spf13/cobra"
)

var workspaceName string

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership workspaces delete" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "delete",
		Short: "Delete the given workspace",
		Run:   deleteFunc,
	}
	cmd.PersistentFlags().StringVarP(&workspaceName, "workspace-name", "w", "", "Name of the workspace to delete")
	return cmd
}

func deleteFunc(cmd *cobra.Command, args []string) {
	token := common.ReadTokenFromFlag(cmd)
	mothershipWorkspaceURL := common.ReadMothershipURLFromFlag(cmd) + "/workspaces"

	cli := goclient.NewHTTP(mothershipWorkspaceURL, token)
	b, err := cli.RequestPath(http.MethodDelete, "/"+workspaceName, nil, nil)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("successfully sent %q: %s\n", http.MethodDelete, string(b))
}
