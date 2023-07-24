// Package list implements list command.
package list

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/olekukonko/tablewriter"

	"github.com/spf13/cobra"
)

var (
	cpath string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership contexts forget" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "Lists the mothership context",
		Run:   listFunc,
	}
	cmd.PersistentFlags().StringVarP(&cpath, "path", "p", common.DefaultContextPath, "Path of the directory to save the context")

	return cmd
}

func listFunc(cmd *cobra.Command, args []string) {
	exists, err := util.CheckPathExists(cpath)
	if err != nil {
		log.Fatalf("failed to check path exists %v", err)
	}

	colums := []string{"name", "URL", "token"}
	rows := [][]string{}

	if exists {
		f, err := os.Open(cpath)
		if err != nil {
			log.Fatalf("failed to open context file %v", err)
		}
		ctxs := common.Contexts{}
		err = json.NewDecoder(f).Decode(&ctxs)
		if err != nil {
			log.Fatalf("failed to decode context file %v", err)
		}
		defer f.Close()

		for _, c := range ctxs.Contexts {
			name := c.Name
			if c.Name == ctxs.Current {
				name = c.Name + " (in use)"
			}
			rows = append(rows, []string{name, c.URL, c.Token})
		}
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
