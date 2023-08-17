// Package enis implements enis command.
package enis

import (
	"github.com/leptonai/lepton/machine/aws/enis/create"
	"github.com/leptonai/lepton/machine/aws/enis/delete"
	"github.com/leptonai/lepton/machine/aws/enis/get"
	"github.com/leptonai/lepton/machine/aws/enis/ls"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpcs" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "enis",
		Short:      "ENI sub-commands",
		Aliases:    []string{"eni", "es", "e", "en", "network-interfaces", "n", "ni", "ns"},
		SuggestFor: []string{"eni", "es", "e", "en", "network-interfaces", "n", "ni", "ns"},
	}

	cmd.AddCommand(
		create.NewCommand(),
		delete.NewCommand(),
		get.NewCommand(),
		ls.NewCommand(),
	)

	return cmd
}
