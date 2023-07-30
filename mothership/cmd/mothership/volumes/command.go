// Package volumes implements volumes command.
package volumes

import (
	"github.com/leptonai/lepton/mothership/cmd/mothership/volumes/list"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership volumes" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "volumes",
		Short: "Sub-commands for Lepton volumes",
	}
	cmd.AddCommand(
		list.NewCommand(),
	)
	return cmd
}
