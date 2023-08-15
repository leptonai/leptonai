// Package delete implements delete command.
package delete

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/prompt"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	workspaceName   string
	workspacePrefix string
	age             uint64
	autoApprove     bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership workspaces delete" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "delete",
		Short:      "Delete the given workspace",
		Aliases:    []string{"del"},
		SuggestFor: []string{"del"},
		Run:        deleteFunc,
	}
	cmd.PersistentFlags().StringVarP(&workspaceName, "workspace-name", "w", "", "Name of the workspace to delete")
	cmd.PersistentFlags().StringVarP(&workspacePrefix, "workspace-prefix", "x", "", "Prefix of the workspaces to delete")
	cmd.PersistentFlags().Uint64VarP(&age, "age", "a", 24, "Minimal age in hours of the workspaces to delete. Only applies when using --workspace-prefix")
	cmd.PersistentFlags().BoolVar(&autoApprove, "auto-approve", false, "Set to auto-approve the action without prompt (if you know what you're doing)")
	return cmd
}

func deleteFunc(cmd *cobra.Command, args []string) {
	if workspaceName == "" && workspacePrefix == "" {
		log.Fatal("workspace name or prefix is required")
	}
	if workspaceName != "" && workspacePrefix != "" {
		log.Fatal("workspace name and prefix cannot be used together")
	}

	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL

	cli := goclient.NewHTTP(mothershipURL, token)

	if workspaceName != "" {
		if !autoApprove {
			if !prompt.IsInputYes(fmt.Sprintf("Confirm to delete a single workspace %q via %q\n", workspaceName, mothershipURL)) {
				return
			}
		}

		b, err := cli.RequestPath(http.MethodDelete, "/workspaces/"+workspaceName, nil, nil)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Printf("successfully sent %q: %s\n", http.MethodDelete, string(b))
		return
	}

	if workspacePrefix != "" {
		b, err := cli.RequestPath(http.MethodGet, "/workspaces", nil, nil)
		if err != nil {
			log.Fatal(err)
		}

		var rs []*crdv1alpha1.LeptonWorkspace
		if err = json.Unmarshal(b, &rs); err != nil {
			log.Fatalf("failed to decode %v", err)
		}

		for _, r := range rs {
			if !strings.HasPrefix(r.Spec.Name, workspacePrefix) {
				continue
			}
			wage := (uint64(time.Now().Unix()) - r.Status.UpdatedAt) / 3600
			if wage < age {
				fmt.Printf("Workspace %s is only %d hours old, skipping\n", r.Spec.Name, wage)
				continue
			}
			if r.Status.State == "deleting" || r.Status.State == "creating" || r.Status.State == "updating" {
				fmt.Printf("Workspace %s is in %s state, skipping\n", r.Spec.Name, r.Status.State)
				continue
			}

			if !autoApprove {
				if !prompt.IsInputYes(fmt.Sprintf("Confirm to delete a workspace %s (by prefix), state: %s, age: %d hours\n", r.Spec.Name, r.Status.State, wage)) {
					continue
				}
			}

			fmt.Printf("Deleting workspace %s\n", r.Spec.Name)
			b, err := cli.RequestPath(http.MethodDelete, "/workspaces/"+r.Spec.Name, nil, nil)
			if err != nil {
				log.Println(err)
			}

			fmt.Printf("successfully sent %q: %s\n", http.MethodDelete, string(b))
		}
	}
}
