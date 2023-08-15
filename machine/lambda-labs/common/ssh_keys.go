package common

import (
	"bytes"
	"sort"

	"github.com/olekukonko/tablewriter"
)

type SSHKey struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type SSHKeys []SSHKey

var SSHKeysColumes = []string{"id", "name"}

func (iss SSHKeys) String() string {
	sort.SliceStable(iss, func(i, j int) bool {
		return iss[i].Name < iss[j].Name
	})

	rows := make([][]string, 0, len(iss))
	for _, v := range iss {
		rows = append(rows, []string{
			v.ID,
			v.Name,
		},
		)
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(SSHKeysColumes)
	tb.AppendBulk(rows)
	tb.Render()

	return buf.String()
}
