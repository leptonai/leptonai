// Package list implements list command.
package list

import (
	"bytes"
	"fmt"
	"log"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/mothership/cmd/mothership/util"

	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
)

var (
	output string
)

func init() {
	cobra.EnablePrefixMatching = true
}

var (
	checkReadiness bool
)

// NewCommand implements "mothership workspace list" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all the workspaces",
		Run:   listFunc,
	}
	cmd.PersistentFlags().StringVarP(&output, "output", "o", "table", "Output format, either 'rawjson' or 'table'")
	cmd.PersistentFlags().BoolVarP(&checkReadiness, "check-readiness", "", false, "true to check if the workspace is ready")

	return cmd
}

func listFunc(cmd *cobra.Command, args []string) {
	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL
	if output != "rawjson" && output != "table" {
		log.Fatalf("invalid output format %q, only 'rawjson' and 'table' are supported", output)
	}

	cli := goclient.NewHTTP(mothershipURL, token)

	if output == "rawjson" {
		b, err := util.ListWorkspacesRaw(cli, checkReadiness)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Println(string(b))
		return
	}

	rs, err := util.ListWorkspaces(cli, checkReadiness)
	if err != nil {
		log.Fatal(err)
	}

	log.Printf("fetched %d workspaces", len(rs))

	colums := []string{"name", "cluster", "deployment-image-tag", "terraform-git-ref", "running-state", "operational-state", "updated at", "description"}
	rows := make([][]string, 0, len(rs))
	for _, c := range rs {
		t := time.Unix(int64(c.Status.UpdatedAt), 0)
		// Format the time as a string using the desired layout
		timeString := t.Format("2006-01-02 15:04:05")
		rows = append(rows, []string{c.Spec.Name, c.Spec.ClusterName, c.Spec.ImageTag, c.Spec.GitRef, string(c.Spec.State), string(c.Status.State), timeString, c.Spec.Description})
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(true)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(colums)
	tb.AppendBulk(rows)
	tb.Render()
	fmt.Println(buf.String())
}
