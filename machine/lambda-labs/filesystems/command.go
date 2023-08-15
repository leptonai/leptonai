// Package filesystems implements filesystems command.
package filesystems

import (
	"github.com/leptonai/lepton/machine/lambda-labs/filesystems/ls"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine lambda-labs filesystems" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "filesystems",
		Short:      "filesystems sub-commands",
		Aliases:    []string{"filesystem", "fs", "file-systems", "fss"},
		SuggestFor: []string{"filesystem", "fs", "file-systems", "fss"},
	}

	cmd.AddCommand(
		ls.NewCommand(),
	)

	return cmd
}
