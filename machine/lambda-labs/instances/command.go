// Package instances implements instances command.
package instances

import (
	"github.com/leptonai/lepton/machine/lambda-labs/instances/create"
	"github.com/leptonai/lepton/machine/lambda-labs/instances/delete"
	"github.com/leptonai/lepton/machine/lambda-labs/instances/get"
	"github.com/leptonai/lepton/machine/lambda-labs/instances/ls"
	"github.com/leptonai/lepton/machine/lambda-labs/instances/types"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine lambda-labs instances" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "instances",
		Short:      "Lambda Labs instances sub-commands",
		Aliases:    []string{"instance", "i", "in", "ins", "inst", "hosts", "host"},
		SuggestFor: []string{"instance", "i", "in", "ins", "inst", "hosts", "host"},
	}

	cmd.AddCommand(
		ls.NewCommand(),
		types.NewCommand(),
		create.NewCommand(),
		get.NewCommand(),
		delete.NewCommand(),
	)

	return cmd
}
