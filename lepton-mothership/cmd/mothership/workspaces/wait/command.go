// Package wait implements wait command.
package wait

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	workspaceName   string
	timeoutInMinute int
	expectedState   string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership workspaces wait" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "wait",
		Short: "wait the given workspace to be in the given state",
		Run:   waitFunc,
	}
	cmd.PersistentFlags().StringVarP(&workspaceName, "workspace-name", "w", "", "Name of the workspace to wait")
	cmd.PersistentFlags().IntVarP(&timeoutInMinute, "timeout", "o", 30, "Timeout in minute")
	cmd.PersistentFlags().StringVarP(&expectedState, "expected-state", "e", "ready", "Expected state of the workspace")
	return cmd
}

func waitFunc(cmd *cobra.Command, args []string) {
	token := common.ReadTokenFromFlag(cmd)
	mothershipWorkspaceURL := common.ReadMothershipURLFromFlag(cmd) + "/workspaces"

	cli := goclient.NewHTTP(mothershipWorkspaceURL, token)
	start := time.Now()
	for {
		if time.Since(start).Minutes() > float64(timeoutInMinute) {
			log.Fatalf("timeout after %d minutes", timeoutInMinute)
		}

		b, err := cli.RequestPath(http.MethodGet, "/"+workspaceName, nil, nil)
		if err != nil {
			log.Printf("failed to get workspace %q: %v", workspaceName, err)
		}
		fmt.Printf("successfully sent %q\n", http.MethodGet)

		w := crdv1alpha1.LeptonWorkspace{}
		err = json.Unmarshal(b, &w)
		if err != nil {
			log.Printf("failed to decode %v", err)
		} else {
			if w.Status.State == crdv1alpha1.LeptonWorkspaceState(expectedState) {
				log.Printf("workspace %q is already in state %q", workspaceName, expectedState)
				return
			} else {
				log.Printf("workspace %q is not in state %q (current %q) yet", workspaceName, expectedState, w.Status.State)
			}
		}

		log.Printf("retrying in 30 seconds...")
		time.Sleep(30 * time.Second)
	}
}
