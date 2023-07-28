// Package wait implements wait command.
package wait

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
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
	if workspaceName == "" {
		log.Fatal("workspace name is required")
	}

	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL

	cli := goclient.NewHTTP(mothershipURL, token)
	start := time.Now()
	for i := 0; ; i++ {
		if time.Since(start).Minutes() > float64(timeoutInMinute) {
			log.Fatalf("timeout after %d minutes", timeoutInMinute)
		}

		if i != 0 {
			log.Printf("%d: waiting for 30 seconds...", i)
			time.Sleep(30 * time.Second)
		}

		b, err := cli.RequestPath(http.MethodGet, "/workspaces/"+workspaceName, nil, nil)
		if err != nil {
			// if expects deleted and server returns 404, we are done
			if crdv1alpha1.LeptonWorkspaceOperationalState(expectedState) == crdv1alpha1.WorkspaceOperationalStateDeleted &&
				// TODO: use status code rather than error message
				strings.Contains(err.Error(), "unexpected HTTP status code 404 with body") {
				return
			}
			log.Printf("failed to get workspace %q: %v", workspaceName, err)
			continue
		}
		fmt.Printf("successfully sent %q\n", http.MethodGet)

		w := crdv1alpha1.LeptonWorkspace{}
		err = json.Unmarshal(b, &w)
		if err != nil {
			log.Printf("failed to decode %v", err)
		} else {
			if w.Status.State == crdv1alpha1.LeptonWorkspaceOperationalState(expectedState) {
				log.Printf("workspace %q is already in state %q", workspaceName, expectedState)
				return
			} else {
				log.Printf("workspace %q is not in state %q (current %q) yet", workspaceName, expectedState, w.Status.State)
			}
		}
	}
}
