// Package sshkeys implements ssh-keys command.
package sshkeys

import (
	"github.com/leptonai/lepton/machine/lambda-labs/ssh-keys/create"
	"github.com/leptonai/lepton/machine/lambda-labs/ssh-keys/delete"
	"github.com/leptonai/lepton/machine/lambda-labs/ssh-keys/ls"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine lambda-labs ssh-keys" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "ssh-keys",
		Short:      "ssh-keys sub-commands",
		Aliases:    []string{"ssh-key", "sshkeys", "sshkey", "ssh", "keys"},
		SuggestFor: []string{"ssh-key", "sshkeys", "sshkey", "ssh", "keys"},
	}

	cmd.AddCommand(
		ls.NewCommand(),
		create.NewCommand(),
		delete.NewCommand(),
	)

	return cmd
}
