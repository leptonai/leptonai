// Package list implements list command.
package list

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership workspace list" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all the workspaces",
		Run:   listFunc,
	}
	return cmd
}

func listFunc(cmd *cobra.Command, args []string) {
	token := common.ReadTokenFromFlag(cmd)
	mothershipWorkspacesURL := common.ReadMothershipURLFromFlag(cmd) + "/workspaces"

	cli := goclient.NewHTTP(mothershipWorkspacesURL, token)
	b, err := cli.RequestURL(http.MethodGet, mothershipWorkspacesURL, nil, nil)
	if err != nil {
		log.Fatal(err)
	}

	var rs []*crdv1alpha1.LeptonWorkspace
	if err = json.Unmarshal(b, &rs); err != nil {
		log.Fatalf("failed to decode %v", err)
	}
	log.Printf("fetched %d workspaces", len(rs))

	colums := []string{"name", "cluster", "deployment-image-tag", "terraform-git-ref", "state", "updated at"}
	rows := make([][]string, 0, len(rs))
	for _, c := range rs {
		t := time.Unix(int64(c.Status.UpdatedAt), 0)
		// Format the time as a string using the desired layout
		timeString := t.Format("2006-01-02 15:04:05")
		rows = append(rows, []string{c.Spec.Name, c.Spec.ClusterName, c.Spec.ImageTag, c.Spec.GitRef, string(c.Status.State), timeString})
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(colums)
	tb.AppendBulk(rows)
	tb.Render()
	fmt.Println(buf.String())
}
