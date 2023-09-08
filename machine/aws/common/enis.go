package common

import (
	"bytes"
	"sort"
	"strings"

	"github.com/olekukonko/tablewriter"
)

type ENI struct {
	ID               string   `json:"id"`
	Description      string   `json:"description"`
	Status           string   `json:"status"`
	AttachmentStatus string   `json:"attachment_status"`
	PrivateIP        string   `json:"private_ip"`
	PrivateDNS       string   `json:"private_dns"`
	VPCID            string   `json:"vpc_id"`
	SubnetID         string   `json:"subnet_id"`
	AvailabilityZone string   `json:"availability_zone"`
	SecurityGroups   []string `json:"security_groups"`
}

type ENIs []ENI

var ENIsCols = []string{"eni id", "eni description", "eni status", "private ip", "private dns", "vpc id", "subnet id", "az", "sgs"}

func (vss ENIs) String() string {
	sort.SliceStable(vss, func(i, j int) bool {
		if vss[i].VPCID == vss[j].VPCID {
			if vss[i].SubnetID == vss[j].SubnetID {
				if vss[i].Status == vss[j].Status {
					return vss[i].Description < vss[j].Description
				}
				return vss[i].Status < vss[j].Status
			}
			return vss[i].SubnetID < vss[j].SubnetID
		}
		return vss[i].VPCID < vss[j].VPCID
	})

	rows := make([][]string, 0, len(vss))
	for _, v := range vss {
		row := []string{
			v.ID,
			v.Description,
			v.Status,
			v.PrivateIP,
			v.PrivateDNS,
			v.VPCID,
			v.SubnetID,
			v.AvailabilityZone,
			strings.Join(v.SecurityGroups, ", "),
		}
		rows = append(rows, row)
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(ENIsCols)
	tb.AppendBulk(rows)
	tb.Render()

	return buf.String()
}
