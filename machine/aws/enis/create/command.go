// Package create implements create command.
package create

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/ec2"
	"github.com/leptonai/lepton/machine/aws/common"

	aws_ec2_types_v2 "github.com/aws/aws-sdk-go-v2/service/ec2/types"
	"github.com/spf13/cobra"
)

var (
	subnetID    string
	sgIDs       []string
	name        string
	description string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpc ls" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "create",
		Short:      "Create an AWS ENI (network interface)",
		Aliases:    []string{"create", "c", "make"},
		SuggestFor: []string{"create", "c", "make"},
		Run:        createFunc,
	}

	cmd.PersistentFlags().StringVarP(&subnetID, "subnet-id", "s", "", "Subnet ID to create the ENI in")
	cmd.PersistentFlags().StringSliceVarP(&sgIDs, "sg-ids", "g", nil, "Security group IDs to attach to the ENI")
	cmd.PersistentFlags().StringVarP(&name, "name", "n", "", "ENI name")
	cmd.PersistentFlags().StringVarP(&description, "description", "d", "", "ENI description")

	return cmd
}

func createFunc(cmd *cobra.Command, args []string) {
	region, err := common.ReadRegion(cmd)
	if err != nil {
		slog.Error("error reading region",
			"error", err,
		)
		os.Exit(1)
	}

	if subnetID == "" {
		slog.Error("empty subnet ID")
		os.Exit(1)
	}
	if len(sgIDs) == 0 {
		slog.Error("empty sg ID")
		os.Exit(1)
	}

	slog.Info("creating a network interface",
		"region", region,
		"name", name,
		"description", description,
		"subnet-id", subnetID,
		"sg-ids", sgIDs,
	)

	cfg, err := aws.New(&aws.Config{
		Region: region,
	})
	if err != nil {
		slog.Error("failed to create aws config",
			"error", err,
		)
		os.Exit(1)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	created, err := ec2.CreateENI(ctx, cfg, subnetID, name, description, sgIDs...)
	cancel()
	if err != nil {
		slog.Error("failed to create ENI",
			"error", err,
		)
		os.Exit(1)
	}
	createdENI := *created.NetworkInterfaceId

	slog.Info("polling for ENI creation",
		"eni-id", createdENI,
	)
	ctx, cancel = context.WithTimeout(context.Background(), 5*time.Minute)
	stopc := make(chan struct{}) // TODO: associate with syscall
	ch := ec2.PollENI(ctx, stopc, cfg, createdENI, aws_ec2_types_v2.NetworkInterfaceStatusAvailable, aws_ec2_types_v2.AttachmentStatus(""), 5*time.Second, 5*time.Second)
	for ev := range ch {
		if ev.Error != nil {
			slog.Error("failed to poll ENI",
				"error", ev.Error,
			)
			os.Exit(1)
		}
		slog.Info("polling ENI",
			"eni", *ev.ENI.NetworkInterfaceId,
		)
	}
	cancel()
	close(stopc)

	// after poll
	ctx, cancel = context.WithTimeout(context.Background(), 10*time.Second)
	v, err := ec2.GetENI(ctx, cfg, createdENI)
	cancel()
	if err != nil {
		slog.Error("failed to get ENI",
			"error", err,
		)
		os.Exit(1)
	}
	attachStatus := ""
	if v.Attachment != nil {
		attachStatus = string(v.Attachment.Status)
	}

	sgs := []string{}
	for _, sg := range v.Groups {
		sgs = append(sgs, *sg.GroupId)
	}

	rss := common.ENIs([]common.ENI{
		{
			ID:               *v.NetworkInterfaceId,
			Description:      *v.Description,
			Status:           string(v.Status),
			AttachmentStatus: attachStatus,
			PrivateIP:        *v.PrivateIpAddress,
			PrivateDNS:       *v.PrivateDnsName,
			VPCID:            *v.VpcId,
			SubnetID:         *v.SubnetId,
			AvailabilityZone: *v.AvailabilityZone,
			SecurityGroups:   sgs,
		},
	})
	fmt.Println(rss.String())
}
