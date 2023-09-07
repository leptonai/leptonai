// Package quotas implements quotas command.
package cost

import (
	"github.com/leptonai/lepton/mothership/cmd/mothership/cost/list"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership quotas" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "cost",
		Short:      "Sub-commands for aws cost",
		Aliases:    []string{"costs"},
		SuggestFor: []string{"cost"},
	}
	cmd.AddCommand(
		list.NewCommand(),
	)
	return cmd
}
