// Package ls implements ls command.
package ls

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

// NewCommand implements "machine aws secrets ls" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "ls",
		Short:      "Lists AWS secrets",
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

	slog.Info("listing secrets", "region", region)

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
	ss, err := secrets.List(ctx, cfg)
	cancel()
	if err != nil {
		slog.Error("failed to list secrets",
			"error", err,
		)
		os.Exit(1)
	}

	for _, s := range ss {
		fmt.Println(s)
	}
}
