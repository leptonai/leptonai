// Package fargate implements fargate command.
package fargate

import (
	"github.com/leptonai/lepton/machine/aws/eks/nodes/fargate/add"
	"github.com/leptonai/lepton/machine/aws/eks/nodes/fargate/hostname"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws eks nodes fargate" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "fargate",
		Short:      "Implements fargate sub-commands",
		Aliases:    []string{"f", "fg"},
		SuggestFor: []string{"f", "fg"},
	}

	cmd.AddCommand(
		add.NewCommand(),
		hostname.NewCommand(),
	)
	return cmd
}
