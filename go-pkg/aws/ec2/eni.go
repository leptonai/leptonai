package ec2

import (
	"context"
	"errors"
	"fmt"
	"log"
	"strings"
	"time"

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

func DeleteENI(ctx context.Context, cfg aws.Config, eniID string) error {
	cli := aws_ec2_v2.NewFromConfig(cfg)

	_, err := cli.DeleteNetworkInterface(ctx,
		&aws_ec2_v2.DeleteNetworkInterfaceInput{
			NetworkInterfaceId: aws.String(eniID),
		},
	)
	if eniNotExist(err) {
		err = nil
	}
	return err
}

// Creates an ENI for a given subnet and security groups.
func CreateENI(ctx context.Context, cfg aws.Config, subnetID string, name string, desc string, sgIDs ...string) (aws_ec2_types_v2.NetworkInterface, error) {
	cli := aws_ec2_v2.NewFromConfig(cfg)
	out, err := cli.CreateNetworkInterface(ctx, &aws_ec2_v2.CreateNetworkInterfaceInput{
		SubnetId:    aws.String(subnetID),
		Groups:      sgIDs,
		Description: aws.String(desc),
		TagSpecifications: []aws_ec2_types_v2.TagSpecification{
			{
				ResourceType: aws_ec2_types_v2.ResourceTypeNetworkInterface,
				Tags: []aws_ec2_types_v2.Tag{
					{
						Key:   aws.String("Name"),
						Value: aws.String(name),
					},
				},
			},
		},
	})
	if err != nil {
		return aws_ec2_types_v2.NetworkInterface{}, err
	}
	return *out.NetworkInterface, nil
}

type ENIStatus struct {
	ENI   aws_ec2_types_v2.NetworkInterface
	Error error
}

// Poll periodically fetches the stack status
// until the stack becomes the desired state.
func PollENI(
	ctx context.Context,
	stopc chan struct{},
	cfg aws.Config,
	eniID string,
	desired aws_ec2_types_v2.NetworkInterfaceStatus,
	desiredAttach aws_ec2_types_v2.AttachmentStatus,
	initialWait time.Duration,
	pollInterval time.Duration,
) <-chan ENIStatus {
	return pollENI(ctx, stopc, cfg, eniID, false, desired, desiredAttach, initialWait, pollInterval)
}

func PollENIDelete(
	ctx context.Context,
	stopc chan struct{},
	cfg aws.Config,
	eniID string,
	initialWait time.Duration,
	pollInterval time.Duration,
) <-chan ENIStatus {
	return pollENI(ctx, stopc, cfg, eniID, true, aws_ec2_types_v2.NetworkInterfaceStatus(""), aws_ec2_types_v2.AttachmentStatus(""), initialWait, pollInterval)
}

func pollENI(
	ctx context.Context,
	stopc chan struct{},
	cfg aws.Config,
	eniID string,
	waitForDelete bool,
	desired aws_ec2_types_v2.NetworkInterfaceStatus,
	desiredAttach aws_ec2_types_v2.AttachmentStatus,
	initialWait time.Duration,
	pollInterval time.Duration,
) <-chan ENIStatus {
	now := time.Now()
	cli := aws_ec2_v2.NewFromConfig(cfg)

	ch := make(chan ENIStatus, 10)
	go func() {
		// very first poll should be no-wait
		// in case stack has already reached desired status
		// wait from second interation
		interval := time.Duration(0)

		first := true
		for ctx.Err() == nil {
			select {
			case <-ctx.Done():
				ch <- ENIStatus{Error: ctx.Err()}
				close(ch)
				return

			case <-stopc:
				ch <- ENIStatus{Error: errors.New("wait stopped")}
				close(ch)
				return

			case <-time.After(interval):
				// very first poll should be no-wait
				// in case stack has already reached desired status
				// wait from second interation
				if interval == time.Duration(0) {
					interval = pollInterval
				}
			}

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
				if eniNotExist(err) {
					log.Printf("ENI does not exist (%v)", err)
					if waitForDelete {
						ch <- ENIStatus{Error: nil}
						close(ch)
						return
					}
				}
				ch <- ENIStatus{Error: err}
				continue
			}

			if len(out.NetworkInterfaces) != 1 {
				if waitForDelete {
					log.Printf("ENI does not exist")
					ch <- ENIStatus{Error: nil}
					close(ch)
					return
				}

				ch <- ENIStatus{Error: fmt.Errorf("expected only 1, unexpected ENI response %+v", out)}
				continue
			}

			eni := out.NetworkInterfaces[0]
			currentStatus := eni.Status
			currentAttachmentStatus := aws_ec2_types_v2.AttachmentStatus("")
			if eni.Attachment != nil {
				currentAttachmentStatus = eni.Attachment.Status
			}
			log.Printf("fetched ENI %s with status %q and attachment status %q (took %v so far)", eniID, currentStatus, currentAttachmentStatus, time.Since(now))

			ch <- ENIStatus{ENI: eni, Error: nil}
			if desired == currentStatus && desiredAttach == currentAttachmentStatus {
				close(ch)
				return
			}

			if first {
				select {
				case <-ctx.Done():
					ch <- ENIStatus{Error: ctx.Err()}
					close(ch)
					return
				case <-stopc:
					ch <- ENIStatus{Error: errors.New("wait stopped")}
					close(ch)
					return
				case <-time.After(initialWait):
				}
				first = false
			}

			// continue for-loop
		}
		ch <- ENIStatus{Error: ctx.Err()}
		close(ch)
	}()
	return ch
}

func eniNotExist(err error) bool {
	if err == nil {
		return false
	}
	return strings.Contains(err.Error(), " does not exist")
}
