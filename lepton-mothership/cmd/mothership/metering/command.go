// Package metering implements metering command.
package metering

import (
	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/metering/get"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership metering" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "metering",
		Short: "Prints out Lepton metering",
	}
	cmd.AddCommand(get.NewCommand())
	return cmd
}
