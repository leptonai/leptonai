package common

import (
	"bytes"
	"fmt"
	"sort"
	"strings"

	"github.com/olekukonko/tablewriter"
)

type InstanceType struct {
	Name            string   `json:"name"`
	Description     string   `json:"description"`
	Regions         []string `json:"regions"`
	PriceUSDPerHour float64  `json:"price_usd_per_hour"`
	VCPU            int32    `json:"vcpu"`
	RAMGiB          int32    `json:"ram_gib"`
	StorageGiB      int32    `json:"storage_gib"`
}

type InstanceTypes []InstanceType

var InstanceTypesColumes = []string{"name", "description", "regions", "price", "vCPUs", "RAM", "Storage"}

func (iss InstanceTypes) String() string {
	sort.SliceStable(iss, func(i, j int) bool {
		return iss[i].PriceUSDPerHour < iss[j].PriceUSDPerHour
	})

	rows := make([][]string, 0, len(iss))
	for _, v := range iss {
		rows = append(rows, []string{
			v.Name,
			v.Description,
			strings.Join(v.Regions, ","),
			fmt.Sprintf("%0.3f UDS/HR", v.PriceUSDPerHour),
			fmt.Sprintf("%d", v.VCPU),
			fmt.Sprintf("%d GiB", v.RAMGiB),
			fmt.Sprintf("%d GiB", v.StorageGiB),
		},
		)
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(InstanceTypesColumes)
	tb.AppendBulk(rows)
	tb.Render()

	return buf.String()
}
