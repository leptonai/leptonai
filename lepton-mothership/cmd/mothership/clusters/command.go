// Package clusters implements clusters command.
package clusters

import (
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/delete"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/get"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "clusters",
		Short: "Implements clusters sub-commands",
	}
	cmd.AddCommand(
		get.NewCommand(),
		delete.NewCommand(),
	)
	return cmd
}
