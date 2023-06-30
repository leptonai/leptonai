// Package token implements token command.
package token

import (
	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/token/forget"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/token/save"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership token" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "token",
		Short: "Implements token sub-commands",
	}
	cmd.AddCommand(
		forget.NewCommand(),
		save.NewCommand(),
	)
	return cmd
}
