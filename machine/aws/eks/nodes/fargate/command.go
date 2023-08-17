// Package fargate implements fargate command.
package fargate

import (
	"github.com/leptonai/lepton/machine/aws/eks/nodes/fargate/add"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership node add" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "fargate",
		Short:      "Implements fargate sub-commands",
		Aliases:    []string{"f", "fg"},
		SuggestFor: []string{"f", "fg"},
	}

	cmd.AddCommand(
		add.NewCommand(),
	)
	return cmd
}
