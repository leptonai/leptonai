// Package hostname implements hostname command.
package hostname

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strings"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/ec2"
	"github.com/leptonai/lepton/machine/aws/common"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws nodes fargate hostname" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "hostname [ENI ID]",
		Short:      "Implements hostname command",
		Aliases:    []string{"host", "hn", "host-name"},
		SuggestFor: []string{"host", "hn", "host-name"},
		Run:        hostnameFunc,
	}
	return cmd
}

func hostnameFunc(cmd *cobra.Command, args []string) {
	region, err := common.ReadRegion(cmd)
	if err != nil {
		slog.Error("error reading region",
			"error", err,
		)
		os.Exit(1)
	}

	if len(args) != 1 {
		slog.Error("eni-id is required as an argument")
		os.Exit(1)
	}
	eniID := args[0]

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
	eni, err := ec2.GetENI(ctx, cfg, eniID)
	cancel()
	if err != nil {
		slog.Error("failed to get ENI",
			"error", err,
		)
		os.Exit(1)
	}

	privateDNS := *eni.PrivateDnsName
	nodeHostname := "fargate-" + strings.ReplaceAll(privateDNS, ".ec2.internal", fmt.Sprintf(".%s.compute.internal", region))
	fmt.Print(nodeHostname)
}
