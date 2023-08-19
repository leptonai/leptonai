// Package eks implements eks command.
package eks

import (
	aws_auth "github.com/leptonai/lepton/machine/aws/eks/aws-auth"
	"github.com/leptonai/lepton/machine/aws/eks/kubeconfig"
	"github.com/leptonai/lepton/machine/aws/eks/ls"
	"github.com/leptonai/lepton/machine/aws/eks/nodes"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws eks" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "eks",
		Short:      "EKS sub-commands",
		Aliases:    []string{"ek", "ekss", "k8s", "ks", "k"},
		SuggestFor: []string{"ek", "ekss", "k8s", "ks", "k"},
	}

	cmd.AddCommand(
		ls.NewCommand(),
		kubeconfig.NewCommand(),
		nodes.NewCommand(),
		aws_auth.NewCommand(),
	)

	return cmd
}
