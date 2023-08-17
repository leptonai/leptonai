package ec2

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_ec2_v2 "github.com/aws/aws-sdk-go-v2/service/ec2"
	aws_ec2_types_v2 "github.com/aws/aws-sdk-go-v2/service/ec2/types"
)

// List ENIs.
func ListENIs(ctx context.Context, cfg aws.Config) ([]aws_ec2_types_v2.NetworkInterface, error) {
	cli := aws_ec2_v2.NewFromConfig(cfg)

	enis := make([]aws_ec2_types_v2.NetworkInterface, 0, 10)
	var nextToken *string = nil
	for i := 0; i < 20; i++ {
		out, err := cli.DescribeNetworkInterfaces(ctx,
			&aws_ec2_v2.DescribeNetworkInterfacesInput{
				NextToken: nextToken,
			},
		)
		if err != nil {
			return nil, err
		}

		enis = append(enis, out.NetworkInterfaces...)

		if nextToken == nil {
			// no more resources are available
			break
		}

		// TODO: add wait to prevent api throttle (rate limit)?
	}

	return enis, nil
}

func GetENI(ctx context.Context, cfg aws.Config, eniID string) (aws_ec2_types_v2.NetworkInterface, error) {
	cli := aws_ec2_v2.NewFromConfig(cfg)

	out, err := cli.DescribeNetworkInterfaces(ctx,
		&aws_ec2_v2.DescribeNetworkInterfacesInput{
			Filters: []aws_ec2_types_v2.Filter{
				{
					Name:   aws.String("network-interface-id"),
					Values: []string{eniID},
				},
			},
		},
	)
	if err != nil {
		return aws_ec2_types_v2.NetworkInterface{}, err
	}

	if len(out.NetworkInterfaces) != 1 {
		return aws_ec2_types_v2.NetworkInterface{}, fmt.Errorf("expected 1 ENI, got %d", len(out.NetworkInterfaces))
	}
	return out.NetworkInterfaces[0], nil
}
