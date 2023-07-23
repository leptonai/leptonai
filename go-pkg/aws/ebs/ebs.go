package ebs

import (
	"context"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	ec2types "github.com/aws/aws-sdk-go-v2/service/ec2/types"
)

// Lists EBS volumes. If notInUseOnly is true, only volumes that are not attached to any instance will be returned.
func ListEBS(ctx context.Context, cfg aws.Config, notInUseOnly bool) ([]ec2types.Volume, error) {
	cli := ec2.NewFromConfig(cfg)

	vs := make([]ec2types.Volume, 0)
	volumeInput := &ec2.DescribeVolumesInput{}
	for {
		volumeOutput, err := cli.DescribeVolumes(ctx, volumeInput)
		if err != nil {
			return nil, err
		}

		vs = append(vs, volumeOutput.Volumes...)
		if volumeOutput.NextToken == nil {
			break
		}
		volumeInput.NextToken = volumeOutput.NextToken
	}

	if !notInUseOnly {
		return vs, nil
	}

	unusedVolumes := make([]ec2types.Volume, 0)
	for _, volume := range vs {
		if len(volume.Attachments) == 0 {
			unusedVolumes = append(unusedVolumes, volume)
		}
	}

	return unusedVolumes, nil
}

// Deletes EBS volumes.
func DeleteVolumes(ctx context.Context, cfg aws.Config, volumes []ec2types.Volume) error {
	cli := ec2.NewFromConfig(cfg)

	for _, volume := range volumes {
		_, err := cli.DeleteVolume(ctx, &ec2.DeleteVolumeInput{
			VolumeId: volume.VolumeId,
		})
		if err != nil {
			return err
		}
	}

	return nil
}
