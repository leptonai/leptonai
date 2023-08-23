// Package ls implements ls command.
package ls

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/machine/aws/common"

	"github.com/spf13/cobra"
)

var (
	limit int
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpc ls" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "ls",
		Short:      "Lists AWS EKS",
		Aliases:    []string{"list", "l"},
		SuggestFor: []string{"list", "l"},
		Run:        lsFunc,
	}
	cmd.PersistentFlags().IntVarP(&limit, "limit", "n", -1, "Set >0 to limit cluster lists")
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
	clusters, err := eks.ListClusters(ctx, region, cfg, limit)
	cancel()
	if err != nil {
		slog.Error("failed to list ENIs",
			"error", err,
		)
		os.Exit(1)
	}

	rss := make(common.EKSClusters, 0, len(clusters))
	for _, v := range clusters {
		rss = append(rss, common.EKSCluster{
			Name:            v.Name,
			Region:          v.Region,
			ARN:             v.ARN,
			Version:         v.Version,
			PlatformVersion: v.PlatformVersion,
			Status:          v.Status,
			Health:          v.Health,
			VPCID:           v.VPCID,
			ClusterSGID:     v.ClusterSGID,
		})
	}
	fmt.Println(rss.String())
}
