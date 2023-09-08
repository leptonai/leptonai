// Package get implements get command.
package get

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/secrets"
	"github.com/leptonai/lepton/machine/aws/common"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpc ls" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "get [secret name]",
		Short:      "Get AWS Secret",
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
	secretName := args[0]
	if secretName == "" {
		slog.Error("empty secret name")
		os.Exit(1)
	}

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
	s, err := secrets.Read(ctx, cfg, secretName)
	cancel()
	if err != nil {
		slog.Error("failed to get VPC",
			"error", err,
		)
		os.Exit(1)
	}
	fmt.Print(s)
}
