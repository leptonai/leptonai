package common

import (
	"bytes"
	"sort"

	"github.com/olekukonko/tablewriter"
)

type EKSCluster struct {
	Name    string `json:"name"`
	Region  string `json:"region"`
	ARN     string `json:"arn"`
	Version string `json:"version"`
	Status  string `json:"status"`
	Health  string `json:"health"`
}

type EKSClusters []EKSCluster

var EKSClustersCols = []string{"name", "region", "arn", "version", "status", "health"}

func (vss EKSClusters) String() string {
	sort.SliceStable(vss, func(i, j int) bool {
		if vss[i].Health == vss[j].Health {
			if vss[i].Status == vss[j].Status {
				if vss[i].Version == vss[j].Version {
					return vss[i].Name < vss[j].Name
				}
				return vss[i].Version < vss[j].Version
			}
			return vss[i].Status < vss[j].Status
		}
		return vss[i].Health < vss[j].Health
	})

	rows := make([][]string, 0, len(vss))
	for _, v := range vss {
		row := []string{
			v.Name,
			v.Region,
			v.ARN,
			v.Version,
			v.Status,
			v.Health,
		}
		rows = append(rows, row)
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(EKSClustersCols)
	tb.AppendBulk(rows)
	tb.Render()

	return buf.String()
}
