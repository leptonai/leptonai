// Package get implements get command.
package get

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/ec2"
	"github.com/leptonai/lepton/machine/aws/common"

	aws_sdk "github.com/aws/aws-sdk-go-v2/aws"
	aws_ec2_types_v2 "github.com/aws/aws-sdk-go-v2/service/ec2/types"
	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpc ls" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "get [VPC ID]",
		Short:      "Get AWS VPCs",
		Aliases:    []string{"get", "ge", "g"},
		SuggestFor: []string{"get", "ge", "g"},
		Run:        getFunc,
	}
	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
	region, err := common.ReadRegion(cmd)
	if err != nil {
		slog.Error("error reading region",
			"error", err,
		)
		os.Exit(1)
	}

	if len(args) != 1 {
		slog.Error("wrong number of arguments -- expected 1")
		os.Exit(1)
	}
	vpcID := args[0]
	if vpcID == "" {
		slog.Error("empty VPC ID")
		os.Exit(1)
	}

	slog.Info("getting VPC/subnets/security groups", "vpc-id", vpcID, "region", region)

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
	vpc, err := ec2.GetVPC(ctx, cfg, vpcID)
	cancel()
	if err != nil {
		slog.Error("failed to get VPC",
			"error", err,
		)
		os.Exit(1)
	}
	vpcName := ""
	for _, tg := range vpc.Tags {
		if *tg.Key == "Name" {
			vpcName = *tg.Value
			break
		}
	}

	ctx, cancel = context.WithTimeout(context.Background(), 10*time.Second)
	subnets, err := ec2.GetVPCSubnets(ctx, cfg, vpcID)
	cancel()
	if err != nil {
		slog.Error("failed to list subnets",
			"error", err,
		)
		os.Exit(1)
	}

	ss := make(common.Subnets, 0, len(subnets))
	for _, s := range subnets {
		subnetName := ""
		for _, tg := range s.Tags {
			if *tg.Key == "Name" {
				subnetName = *tg.Value
				break
			}
		}
		ss = append(ss, common.Subnet{
			ID:               *s.SubnetId,
			Name:             subnetName,
			AvailabilityZone: *s.AvailabilityZone,
			State:            string(s.State),
		})
	}
	rss := common.VPCs([]common.VPC{
		{
			ID:      vpcID,
			Name:    vpcName,
			State:   string(vpc.State),
			Subnets: ss,
		},
	})
	fmt.Println(rss.String())

	ctx, cancel = context.WithTimeout(context.Background(), 10*time.Second)
	sgs, err := ec2.ListSGs(ctx, cfg,
		aws_ec2_types_v2.Filter{
			Name:   aws_sdk.String("vpc-id"),
			Values: []string{vpcID},
		},
	)
	cancel()
	if err != nil {
		slog.Error("failed to list subnets",
			"error", err,
		)
		os.Exit(1)
	}

	sgss := make(common.SGs, 0, len(sgs))
	for _, sv := range sgs {
		sgss = append(sgss, common.SG{
			VPCID:       vpcID,
			ID:          *sv.GroupId,
			Name:        *sv.GroupName,
			Description: *sv.Description,
		})
	}
	fmt.Println(sgss.String())
}
