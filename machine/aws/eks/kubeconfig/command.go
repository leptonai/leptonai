// Package kubeconfig implements kubeconfig command.
package kubeconfig

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/machine/aws/common"

	"github.com/spf13/cobra"
	"sigs.k8s.io/yaml"
)

var (
	region     string
	kubeconfig string
)

var (
	homeDir, _        = os.UserHomeDir()
	defaultKubeconfig = filepath.Join(homeDir, ".kube", "config")
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine eks kubeconfig" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "kubeconfig [cluster name]",
		Short:      "Fetches the kubeconfig",
		Aliases:    []string{"k", "kubeconf", "kube-config", "kubeconfig"},
		SuggestFor: []string{"k", "kubeconf", "kube-config", "kubeconfig"},
		Run:        kubeconfigFunc,
	}

	cmd.PersistentFlags().StringVarP(&region, "region", "r", "us-east-1", "AWS region")
	cmd.PersistentFlags().StringVarP(&kubeconfig, "kubeconfig", "k", "", "kubeconfig path to write to")

	return cmd
}

func kubeconfigFunc(cmd *cobra.Command, args []string) {
	region, err := common.ReadRegion(cmd)
	if err != nil {
		slog.Error("error reading region",
			"error", err,
		)
		os.Exit(1)
	}

	if len(args) != 1 {
		slog.Error("cluster-name is required as an argument")
		os.Exit(1)
	}
	clusterName := args[0]

	if kubeconfig == "" {
		kubeconfig = filepath.Join(homeDir, ".kube", clusterName+".config")
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
	cluster, err := eks.GetCluster(ctx, cfg, clusterName)
	cancel()
	if err != nil {
		slog.Error("failed to get EKS cluster",
			"error", err,
		)
		os.Exit(1)
	}

	kcfg, err := cluster.Kubeconfig()
	if err != nil {
		slog.Error("failed to get EKS cluster kubeconfig",
			"error", err,
		)
		os.Exit(1)
	}
	b, err := yaml.Marshal(kcfg)
	if err != nil {
		slog.Error("failed to marshal kubeconfig",
			"error", err,
		)
		os.Exit(1)
	}

	if err = os.WriteFile(kubeconfig, b, 0644); err != nil {
		slog.Error("failed to write kubeconfig",
			"error", err,
		)
		os.Exit(1)
	}
	slog.Info("successfully wrote kubeconfig",
		"kubeconfig", kubeconfig,
	)

	fmt.Printf("\ncp %s %s\nkubectl get nodes\n\n", kubeconfig, defaultKubeconfig)
}
