package ec2

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_ec2_v2 "github.com/aws/aws-sdk-go-v2/service/ec2"
	aws_ec2_types_v2 "github.com/aws/aws-sdk-go-v2/service/ec2/types"
)

// List security groups.
func ListSGs(ctx context.Context, cfg aws.Config, filters ...aws_ec2_types_v2.Filter) ([]aws_ec2_types_v2.SecurityGroup, error) {
	cli := aws_ec2_v2.NewFromConfig(cfg)

	vpcs := make([]aws_ec2_types_v2.SecurityGroup, 0, 10)
	var nextToken *string = nil
	for i := 0; i < 20; i++ {
		out, err := cli.DescribeSecurityGroups(ctx,
			&aws_ec2_v2.DescribeSecurityGroupsInput{
				NextToken: nextToken,
				Filters:   filters,
			},
		)
		if err != nil {
			return nil, err
		}

		vpcs = append(vpcs, out.SecurityGroups...)

		if nextToken == nil {
			// no more resources are available
			break
		}

		// TODO: add wait to prevent api throttle (rate limit)?
	}

	return vpcs, nil
}

func GetSG(ctx context.Context, cfg aws.Config, sgID string) (aws_ec2_types_v2.SecurityGroup, error) {
	cli := aws_ec2_v2.NewFromConfig(cfg)

	out, err := cli.DescribeSecurityGroups(ctx,
		&aws_ec2_v2.DescribeSecurityGroupsInput{
			Filters: []aws_ec2_types_v2.Filter{
				{
					Name:   aws.String("group-id"),
					Values: []string{sgID},
				},
			},
		},
	)
	if err != nil {
		return aws_ec2_types_v2.SecurityGroup{}, err
	}

	if len(out.SecurityGroups) != 1 {
		return aws_ec2_types_v2.SecurityGroup{}, fmt.Errorf("expected 1 security group, got %d", len(out.SecurityGroups))
	}
	return out.SecurityGroups[0], nil
}
