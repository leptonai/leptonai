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
		Short:      "Lists AWS ENIs (network interfaces)",
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

	slog.Info("listing network interfaces (ENIs)", "region", region)

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
	enis, err := ec2.ListENIs(ctx, cfg)
	cancel()
	if err != nil {
		slog.Error("failed to list ENIs",
			"error", err,
		)
		os.Exit(1)
	}

	rss := make(common.ENIs, 0, len(enis))
	for _, v := range enis {
		attachStatus := ""
		if v.Attachment != nil {
			attachStatus = string(v.Attachment.Status)
		}

		sgs := []string{}
		for _, sg := range v.Groups {
			sgs = append(sgs, *sg.GroupId)
		}

		rss = append(rss, common.ENI{
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
		})
	}
	fmt.Println(rss.String())
}
