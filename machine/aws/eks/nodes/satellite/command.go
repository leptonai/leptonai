// Package satellite implements satellite command.
package satellite

import (
	"github.com/leptonai/lepton/machine/aws/eks/nodes/satellite/add"
	"github.com/leptonai/lepton/machine/aws/eks/nodes/satellite/hostname"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws eks nodes satellite" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "satellite",
		Short:      "Implements satellite sub-commands",
		Aliases:    []string{"s", "st", "satel", "f", "fg"},
		SuggestFor: []string{"s", "st", "satel", "f", "fg"},
	}

	cmd.AddCommand(
		add.NewCommand(),
		hostname.NewCommand(),
	)
	return cmd
}
