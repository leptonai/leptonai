package common

import (
	"bytes"
	"sort"

	"github.com/olekukonko/tablewriter"
)

type Subnet struct {
	ID               string `json:"id"`
	Name             string `json:"name"`
	AvailabilityZone string `json:"availability_zone"`
	State            string `json:"state"`
}

type Subnets []Subnet

type VPC struct {
	ID      string  `json:"id"`
	Name    string  `json:"name"`
	State   string  `json:"state"`
	Subnets Subnets `json:"subnets"`
}

type VPCs []VPC

var VPCsCols = []string{"vpc id", "vpc name", "vpc state", "subnet id", "subnet name", "subnet az", "subnet state"}

func (vss VPCs) String() string {
	sort.SliceStable(vss, func(i, j int) bool {
		if vss[i].Name == vss[j].Name {
			return vss[i].ID < vss[j].ID
		}
		return vss[i].Name < vss[j].Name
	})

	rows := make([][]string, 0, len(vss))
	for _, v := range vss {
		sort.SliceStable(v.Subnets, func(i, j int) bool {
			if v.Subnets[i].Name == v.Subnets[j].Name {
				return v.Subnets[i].AvailabilityZone < v.Subnets[j].AvailabilityZone
			}
			return v.Subnets[i].Name < v.Subnets[j].Name
		})

		for _, s := range v.Subnets {
			row := []string{
				v.ID,
				v.Name,
				v.State,
				s.ID,
				s.Name,
				s.AvailabilityZone,
				s.State,
			}
			rows = append(rows, row)
		}
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(VPCsCols)
	tb.AppendBulk(rows)
	tb.Render()

	return buf.String()
}
