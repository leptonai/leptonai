// Package efs implements EFS utils.
package efs

import (
	"bytes"
	"context"
	"fmt"
	"sort"
	"time"

	goutil "github.com/leptonai/lepton/go-pkg/util"

	aws_efs_v2 "github.com/aws/aws-sdk-go-v2/service/efs"
	"github.com/dustin/go-humanize"
	"github.com/olekukonko/tablewriter"
)

const describeInterval = 5 * time.Second

func ListFileSystems(ctx context.Context, cli *aws_efs_v2.Client) ([]FileSystem, error) {
	fss := make([]FileSystem, 0)
	var nextMarker *string = nil
	for i := 0; i < 10; i++ {
		out, err := cli.DescribeFileSystems(ctx, &aws_efs_v2.DescribeFileSystemsInput{
			Marker: nextMarker,
		})
		if err != nil {
			return nil, err
		}
		for _, f := range out.FileSystems {
			size := uint64(0)
			if f.SizeInBytes != nil && f.SizeInBytes.Value > 0 {
				size = uint64(f.SizeInBytes.Value)
			}
			fs := FileSystem{
				Name: *f.Name,
				ARN:  *f.FileSystemArn,
				ID:   *f.FileSystemId,

				SizeInUse:      humanize.Bytes(size),
				SizeInUseBytes: size,

				Tags: make(map[string]string),
			}
			for _, tag := range f.Tags {
				fs.Tags[*tag.Key] = *tag.Value
			}

			out2, err := cli.DescribeMountTargets(ctx, &aws_efs_v2.DescribeMountTargetsInput{
				FileSystemId: &fs.ID,
			})
			if err != nil {
				return nil, err
			}
			for _, mt := range out2.MountTargets {
				fs.MoutTargets = append(fs.MoutTargets, MoutTarget{
					FileSystemID:     *mt.FileSystemId,
					ID:               *mt.MountTargetId,
					State:            string(mt.LifeCycleState),
					AvailabilityZone: *mt.AvailabilityZoneName,
				})
			}
			sort.SliceStable(fs.MoutTargets, func(i, j int) bool {
				if fs.MoutTargets[i].AvailabilityZone == fs.MoutTargets[j].AvailabilityZone {
					return fs.MoutTargets[i].ID < fs.MoutTargets[j].ID
				}
				return fs.MoutTargets[i].AvailabilityZone < fs.MoutTargets[j].AvailabilityZone
			})

			fss = append(fss, fs)
		}

		nextMarker = out.NextMarker
		if nextMarker == nil {
			// no more resources are available
			break
		}

		time.Sleep(describeInterval)
	}

	goutil.Logger.Debugw("listed EFS filesystems",
		"filesystems", len(fss),
	)
	return fss, nil
}

func DeleteFileSystem(ctx context.Context, cli *aws_efs_v2.Client, fsIDs []string) error {
	var err error
	for _, fsID := range fsIDs {
		_, err = cli.DeleteFileSystem(ctx, &aws_efs_v2.DeleteFileSystemInput{
			FileSystemId: &fsID,
		})
		if err != nil {
			goutil.Logger.Errorw("failed to delete EFS filesystem",
				"filesystem_id", fsID,
			)
		}

		goutil.Logger.Debugw("deleted EFS filesystem",
			"filesystem_id", fsID,
		)
	}

	return nil
}

// Does not need to AZ at filesystem level.
// AZ is defined at the mount target level.
type FileSystem struct {
	Name string `json:"name"`
	ARN  string `json:"arn"`
	ID   string `json:"id"`

	SizeInUse      string `json:"size_in_use"`
	SizeInUseBytes uint64 `json:"size_in_use_bytes"`

	Tags map[string]string `json:"tags"`

	MoutTargets []MoutTarget `json:"mount_targets"`
}

type MoutTarget struct {
	FileSystemID     string `json:"file_system_id"`
	ID               string `json:"id"`
	State            string `json:"state"`
	AvailabilityZone string `json:"availability_zone"`
}

func (fs FileSystem) String() string {
	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetRowLine(true)
	tb.Append([]string{"VOLUME KIND", "EFS"})
	tb.Append([]string{"FILESYSTEM NAME", fs.Name})
	tb.Append([]string{"FILESYSTEM ARN", fs.ARN})
	tb.Append([]string{"FILESYSTEM ID", fs.ID})
	tb.Append([]string{"FILESYSTEM SIZE IN USE", fs.SizeInUse})
	for k, v := range fs.Tags {
		tb.Append([]string{fmt.Sprintf("FILESYSTEM TAG %q", k), v})
	}
	tb.Render()

	rs := buf.String()

	if len(fs.MoutTargets) == 0 {
		return rs
	}

	for i, target := range fs.MoutTargets {
		buf.Reset()
		tb := tablewriter.NewWriter(buf)
		tb.SetAutoWrapText(false)
		tb.SetAlignment(tablewriter.ALIGN_LEFT)
		tb.SetCenterSeparator("*")
		tb.SetRowLine(true)
		tb.Append([]string{fmt.Sprintf("MOUNT TARGET FILESYSTEM ID #%d", i+1), target.FileSystemID})
		tb.Append([]string{fmt.Sprintf("MOUNT TARGET ID #%d", i+1), target.ID})
		tb.Append([]string{fmt.Sprintf("MOUNT TARGET STATE #%d", i+1), target.State})
		tb.Append([]string{fmt.Sprintf("MOUNT TARGET AZ #%d", i+1), target.AvailabilityZone})
		tb.Render()

		rs += "\n"
		rs += buf.String()
	}

	return rs
}
