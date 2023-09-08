// Package addrole implements addrole command.
package addrole

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
	"k8s.io/client-go/kubernetes"
	aws_auth_config "sigs.k8s.io/aws-iam-authenticator/pkg/config"
	aws_auth_client "sigs.k8s.io/aws-iam-authenticator/pkg/mapper/configmap/client"
	"sigs.k8s.io/yaml"
)

var (
	clusterName string

	roleARN  string
	userID   string
	groups   []string
	username string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws nodes fargate add" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "add",
		Short:      "Implements add sub-commands (manually add/apply fargate node object)",
		Aliases:    []string{"a", "ad", "apply", "create"},
		SuggestFor: []string{"a", "ad", "apply", "create"},
		Run:        addFunc,
	}

	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "AWS EKS cluster name")

	cmd.PersistentFlags().StringVar(&roleARN, "role-arn", "", "AWS Resource Name of the role")
	cmd.PersistentFlags().StringVar(&userID, "user-id", "", "AWS PrincipalId of the user")

	cmd.PersistentFlags().StringSliceVar(&groups, "groups", []string{"system:bootstrappers", "system:nodes"}, "list of Kubernetes groups this role will authenticate")
	cmd.PersistentFlags().StringVar(&username, "user-name", "", "username pattern that this instances assuming in Kubernetes")

	return cmd
}

func addFunc(cmd *cobra.Command, args []string) {
	if len(clusterName) == 0 {
		slog.Error("cluster-name is required")
		os.Exit(1)
	}
	if len(roleARN) == 0 && len(userID) == 0 {
		slog.Error("both role-arn and user-id are empty -- either one is required")
		os.Exit(1)
	}
	if len(roleARN) != 0 && len(userID) != 0 {
		slog.Error("both role-arn and user-id are non-empty -- only one is required")
		os.Exit(1)
	}
	if len(groups) == 0 {
		slog.Error("groups is required")
		os.Exit(1)
	}
	if len(username) == 0 {
		slog.Error("user-name is required")
		os.Exit(1)
	}

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

	slog.Info("adding a role entry to aws-auth configmap",
		"user-id", userID,
		"role-arn", roleARN,
		"groups", groups,
		"username", username,
	)
	awsAuthCli := aws_auth_client.New(clientset.CoreV1().ConfigMaps("kube-system"))
	configMap, err := awsAuthCli.AddRole(&aws_auth_config.RoleMapping{
		UserId:  userID,
		RoleARN: roleARN,

		Username: username,
		Groups:   groups,
	})
	if err != nil {
		slog.Error("failed to add role to aws-auth configmap",
			"error", err,
		)
		os.Exit(1)
	}

	slog.Info("successfully updated aws-auth configmap")
	b, err = yaml.Marshal(configMap)
	if err != nil {
		slog.Error("failed to marshal configmap",
			"error", err,
		)
		os.Exit(1)
	}
	fmt.Println(string(b))
}
