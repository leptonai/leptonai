// Package delete implements delete command.
package delete

import (
	"context"
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
		Use:        "delete [ENI ID]",
		Short:      "deletes an AWS ENI (network interface)",
		Aliases:    []string{"del", "de", "d"},
		SuggestFor: []string{"del", "de", "d"},
		Run:        deleteFunc,
	}
	return cmd
}

func deleteFunc(cmd *cobra.Command, args []string) {
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

	slog.Info("deleting network interface", "eni-id", eniID, "region", region)

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
	err = ec2.DeleteENI(ctx, cfg, eniID)
	cancel()
	if err != nil {
		slog.Error("failed to delete ENI",
			"error", err,
		)
		os.Exit(1)
	}

	slog.Info("polling for ENI deletion",
		"eni-id", eniID,
	)
	ctx, cancel = context.WithTimeout(context.Background(), 5*time.Minute)
	stopc := make(chan struct{}) // TODO: associate with syscall
	ch := ec2.PollENIDelete(ctx, stopc, cfg, eniID, 5*time.Second, 5*time.Second)
	for ev := range ch {
		if ev.Error != nil {
			slog.Error("failed to poll ENI",
				"error", ev.Error,
			)
			os.Exit(1)
		}
		slog.Info("polling ENI",
			"eni", eniID,
		)
	}
	cancel()
	close(stopc)

	slog.Info("successfully deleted ENI",
		"eni-id", eniID,
	)
}

// TODO: support for detachment
