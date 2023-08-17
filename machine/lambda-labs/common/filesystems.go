package common

import (
	"bytes"
	"fmt"
	"sort"

	openapiclient "github.com/leptonai/lepton/go-pkg/openapi/lambdalabs"

	"github.com/olekukonko/tablewriter"
)

type Filesystem = openapiclient.FileSystem

type Filesystems []Filesystem

var FilesystemsCols = []string{"id", "name", "created", "created by", "mount point", "region", "in-use"}

func (iss Filesystems) String() string {
	sort.SliceStable(iss, func(i, j int) bool {
		return iss[i].Created < iss[j].Created
	})

	rows := make([][]string, 0, len(iss))
	for _, v := range iss {
		rows = append(rows, []string{
			v.Id,
			v.Name,
			v.Created,
			fmt.Sprintf("%s (id %s, status %s)", v.CreatedBy.Email, v.CreatedBy.Id, v.CreatedBy.Status),
			v.MountPoint,
			v.Region.Name,
			fmt.Sprintf("%v", v.IsInUse),
		})
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(FilesystemsCols)
	tb.AppendBulk(rows)
	tb.Render()

	return buf.String()
}
