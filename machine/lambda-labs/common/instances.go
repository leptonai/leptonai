package common

import (
	"bytes"
	"sort"
	"strings"

	"github.com/olekukonko/tablewriter"
)

type Instance struct {
	ID          string   `json:"id"`
	InstaceType string   `json:"instance_type"`
	Status      string   `json:"status"`
	Region      string   `json:"region"`
	SSHKeys     []string `json:"ssh_keys"`
	FileSystems []string `json:"file_systems"`
	Hostname    string   `json:"hostname"`
}

type Instances []Instance

var InstancesColumes = []string{"id", "instance type", "status", "region", "ssh keys", "file systems", "hostname"}

func (iss Instances) String() string {
	sort.SliceStable(iss, func(i, j int) bool {
		if iss[i].Region == iss[j].Region {
			if iss[i].Status == iss[j].Status {
				if iss[i].InstaceType == iss[j].InstaceType {
					return iss[i].ID < iss[j].ID
				}
				return iss[i].InstaceType < iss[j].InstaceType
			}
			return iss[i].Status < iss[j].Status
		}
		return iss[i].Region < iss[j].Region
	})

	rows := make([][]string, 0, len(iss))
	for _, v := range iss {
		rows = append(rows, []string{
			v.ID,
			v.InstaceType,
			v.Status,
			v.Region,
			strings.Join(v.SSHKeys, ","),
			strings.Join(v.FileSystems, ","),
			v.Hostname,
		},
		)
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(InstancesColumes)
	tb.AppendBulk(rows)
	tb.Render()

	return buf.String()
}
