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

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpc ls" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "get [ENI ID]",
		Short:      "Get AWS ENI (network interface)",
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
	eniID := args[0]
	if eniID == "" {
		slog.Error("empty ENI ID")
		os.Exit(1)
	}

	slog.Info("getting network interface", "eni-id", eniID, "region", region)

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
	v, err := ec2.GetENI(ctx, cfg, eniID)
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
