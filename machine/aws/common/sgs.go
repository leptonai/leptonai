package common

import (
	"bytes"
	"sort"

	"github.com/olekukonko/tablewriter"
)

type SG struct {
	VPCID       string `json:"vpc_id"`
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
}

type SGs []SG

var SGsCols = []string{"vpc id", "sg id", "sg name", "sg description"}

func (sgss SGs) String() string {
	sort.SliceStable(sgss, func(i, j int) bool {
		if sgss[i].VPCID == sgss[j].VPCID {
			if sgss[i].Name == sgss[j].Name {
				return sgss[i].Description < sgss[j].Description
			}
			return sgss[i].Name < sgss[j].Name
		}
		return sgss[i].VPCID < sgss[j].VPCID
	})

	rows := make([][]string, 0, len(sgss))
	for _, v := range sgss {
		rows = append(rows, []string{
			v.VPCID,
			v.ID,
			v.Name,
			v.Description,
		})
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(SGsCols)
	tb.AppendBulk(rows)
	tb.Render()

	return buf.String()
}
