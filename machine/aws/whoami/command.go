// Package whoami implements whoami command.
package whoami

import (
	"context"
	"log/slog"
	"os"
	"time"

	aws_sts_v2 "github.com/aws/aws-sdk-go-v2/service/sts"
	"github.com/leptonai/lepton/go-pkg/aws"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpcs" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "whoami",
		Short:      "Prints the current identity",
		Aliases:    []string{"who", "i", "who-am-i", "w"},
		SuggestFor: []string{"who", "i", "who-am-i", "w"},
		Run:        whoFunc,
	}

	return cmd
}

func whoFunc(cmd *cobra.Command, args []string) {
	cfg, err := aws.New(&aws.Config{Region: "us-east-1"})
	if err != nil {
		slog.Error("error reading region",
			"error", err,
		)
		os.Exit(1)
	}
	cli := aws_sts_v2.NewFromConfig(cfg)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	out, err := cli.GetCallerIdentity(ctx, &aws_sts_v2.GetCallerIdentityInput{})
	cancel()
	if err != nil {
		slog.Error("failed to get aws caller identity",
			"error", err,
		)
		os.Exit(1)
	}

	slog.Info("AWS caller identity",
		"account", *out.Account,
		"arn", *out.Arn,
		"user-id", *out.UserId,
	)
}
