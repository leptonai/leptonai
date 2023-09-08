// Package ls implements ls command.
package ls

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/ec2"
	"github.com/leptonai/lepton/machine/aws/common"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpc ls" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "ls",
		Short:      "Lists AWS VPCs",
		Aliases:    []string{"list", "l"},
		SuggestFor: []string{"list", "l"},
		Run:        lsFunc,
	}
	return cmd
}

func lsFunc(cmd *cobra.Command, args []string) {
	region, err := common.ReadRegion(cmd)
	if err != nil {
		slog.Error("error reading region",
			"error", err,
		)
		os.Exit(1)
	}

	slog.Info("listing VPCs", "region", region)

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
	vpcs, err := ec2.ListVPCs(ctx, cfg)
	cancel()
	if err != nil {
		slog.Error("failed to list VPCs",
			"error", err,
		)
		os.Exit(1)
	}

	rss := make(common.VPCs, 0, len(vpcs))
	for _, v := range vpcs {
		vpcID := *v.VpcId
		vpcName := ""
		for _, tg := range v.Tags {
			if *tg.Key == "Name" {
				vpcName = *tg.Value
				break
			}
		}
		slog.Info("querying subnets for the VPC", "vpc-name", vpcName, "vpc-id", vpcID)

		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		subnets, err := ec2.GetVPCSubnets(ctx, cfg, *v.VpcId)
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

		rss = append(rss, common.VPC{
			ID:      vpcID,
			Name:    vpcName,
			State:   string(v.State),
			Subnets: ss,
		})
	}
	fmt.Println(rss.String())
}
