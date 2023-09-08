// Package get implements get command.
package get

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/machine/aws/common"
	mothership_common "github.com/leptonai/lepton/mothership/cmd/mothership/common"

	"github.com/spf13/cobra"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"sigs.k8s.io/yaml"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws eks aws-auth get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "get [cluster name]",
		Short:      "Implements get command",
		Aliases:    []string{"g", "ge", "read"},
		SuggestFor: []string{"g", "ge", "read"},
		Run:        getFunc,
	}

	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
	if len(args) != 1 {
		slog.Error("cluster-name is required")
		os.Exit(1)
	}
	clusterName := args[0]

	region, err := common.ReadRegion(cmd)
	if err != nil {
		slog.Error("error reading region",
			"error", err,
		)
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

	f, err := os.CreateTemp(os.TempDir(), "tmp-kubeconfig")
	if err != nil {
		slog.Error("failed to create a temp file",
			"error", err,
		)
		os.Exit(1)
	}
	if _, err = f.Write(b); err != nil {
		slog.Error("failed to write kubeconfig to a temp file",
			"error", err,
		)
		os.Exit(1)
	}
	if err = f.Sync(); err != nil {
		slog.Error("failed to sync kubeconfig to a temp file",
			"error", err,
		)
		os.Exit(1)
	}
	slog.Info("successfully wrote kubeconfig to a temp file",
		"path", f.Name(),
	)
	kubeconfigPath := f.Name()

	restConfig, clusterARN, err := mothership_common.BuildRestConfig(kubeconfigPath)
	if err != nil {
		slog.Error("failed to build rest config from kubeconfig",
			"error", err,
		)
		os.Exit(1)
	}
	slog.Info("successfully built rest config from kubeconfig", "arn", clusterARN)

	clientset, err := kubernetes.NewForConfig(restConfig)
	if err != nil {
		slog.Error("failed to create kubernetes clientset",
			"error", err,
		)
		os.Exit(1)
	}

	ctx, cancel = context.WithTimeout(context.Background(), 10*time.Second)
	out, err := clientset.CoreV1().ConfigMaps("kube-system").Get(ctx, "aws-auth", metav1.GetOptions{})
	cancel()
	if err != nil {
		slog.Error("failed to get aws-auth configmap",
			"error", err,
		)
		os.Exit(1)
	}

	b, err = yaml.Marshal(out)
	if err != nil {
		slog.Error("failed to marshal aws-auth configmap",
			"error", err,
		)
		os.Exit(1)
	}
	fmt.Println(string(b))
}
