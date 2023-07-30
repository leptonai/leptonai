// Package contexts implements contexts command.
package contexts

import (
	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/mothership/cmd/mothership/contexts/forget"
	"github.com/leptonai/lepton/mothership/cmd/mothership/contexts/list"
	"github.com/leptonai/lepton/mothership/cmd/mothership/contexts/save"
	"github.com/leptonai/lepton/mothership/cmd/mothership/contexts/use"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership contexts" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "contexts",
		Short: "Implements context sub-commands",
	}
	cmd.AddCommand(
		forget.NewCommand(),
		save.NewCommand(),
		list.NewCommand(),
		use.NewCommand(),
	)
	return cmd
}
