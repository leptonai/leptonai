// Package secrets implements secrets command.
package secrets

import (
	"github.com/leptonai/lepton/machine/aws/secrets/get"
	"github.com/leptonai/lepton/machine/aws/secrets/ls"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpcs" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "secrets",
		Short:      "VPC and subnets sub-commands",
		Aliases:    []string{"secret", "ss", "s", "sss"},
		SuggestFor: []string{"secret", "ss", "s", "sss"},
	}

	cmd.AddCommand(
		get.NewCommand(),
		ls.NewCommand(),
	)

	return cmd
}
