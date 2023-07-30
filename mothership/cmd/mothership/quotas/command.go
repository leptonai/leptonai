// Package quotas implements quotas command.
package quotas

import (
	"github.com/leptonai/lepton/mothership/cmd/mothership/quotas/list"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership quotas" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "quotas",
		Short: "Sub-commands for Lepton quotas",
	}
	cmd.AddCommand(
		list.NewCommand(),
	)
	return cmd
}
