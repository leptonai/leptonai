// Package nodes implements nodes command.
package nodes

import (
	"github.com/leptonai/lepton/machine/aws/eks/nodes/fargate"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership node" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "nodes",
		Short:      "Implements nodes sub-commands",
		Aliases:    []string{"node", "n", "nd"},
		SuggestFor: []string{"node", "n", "nd"},
	}

	cmd.AddCommand(
		fargate.NewCommand(),
	)
	return cmd
}
