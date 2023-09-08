package ec2

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_ec2_v2 "github.com/aws/aws-sdk-go-v2/service/ec2"
	aws_ec2_types_v2 "github.com/aws/aws-sdk-go-v2/service/ec2/types"
)

// List VPCs.
func ListVPCs(ctx context.Context, cfg aws.Config) ([]aws_ec2_types_v2.Vpc, error) {
	cli := aws_ec2_v2.NewFromConfig(cfg)

	vpcs := make([]aws_ec2_types_v2.Vpc, 0, 10)
	var nextToken *string = nil
	for i := 0; i < 20; i++ {
		out, err := cli.DescribeVpcs(ctx,
			&aws_ec2_v2.DescribeVpcsInput{
				NextToken: nextToken,
			},
		)
		if err != nil {
			return nil, err
		}

		vpcs = append(vpcs, out.Vpcs...)

		if nextToken == nil {
			// no more resources are available
			break
		}

		// TODO: add wait to prevent api throttle (rate limit)?
	}

	return vpcs, nil
}

func GetVPC(ctx context.Context, cfg aws.Config, vpcID string) (aws_ec2_types_v2.Vpc, error) {
	cli := aws_ec2_v2.NewFromConfig(cfg)

	out, err := cli.DescribeVpcs(ctx,
		&aws_ec2_v2.DescribeVpcsInput{
			Filters: []aws_ec2_types_v2.Filter{
				{
					Name:   aws.String("vpc-id"),
					Values: []string{vpcID},
				},
			},
		},
	)
	if err != nil {
		return aws_ec2_types_v2.Vpc{}, err
	}

	if len(out.Vpcs) != 1 {
		return aws_ec2_types_v2.Vpc{}, fmt.Errorf("expected 1 VPC, got %d", len(out.Vpcs))
	}
	return out.Vpcs[0], nil
}

func GetVPCSubnets(ctx context.Context, cfg aws.Config, vpcID string) ([]aws_ec2_types_v2.Subnet, error) {
	cli := aws_ec2_v2.NewFromConfig(cfg)

	out, err := cli.DescribeVpcs(ctx,
		&aws_ec2_v2.DescribeVpcsInput{
			Filters: []aws_ec2_types_v2.Filter{
				{
					Name:   aws.String("vpc-id"),
					Values: []string{vpcID},
				},
			},
		},
	)
	if err != nil {
		return nil, err
	}

	if len(out.Vpcs) != 1 {
		return nil, fmt.Errorf("expected 1 VPC, got %d", len(out.Vpcs))
	}
	vpc := out.Vpcs[0]

	out2, err := cli.DescribeSubnets(ctx,
		&aws_ec2_v2.DescribeSubnetsInput{
			Filters: []aws_ec2_types_v2.Filter{
				{
					Name:   aws.String("vpc-id"),
					Values: []string{*vpc.VpcId},
				},
			},
		},
	)
	if err != nil {
		return nil, err
	}

	return out2.Subnets, nil
}
