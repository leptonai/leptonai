// Package: lambdalabs implements "lambda-labs" commands.
package lambdalabs

import (
	"github.com/leptonai/lepton/machine/lambda-labs/common"
	"github.com/leptonai/lepton/machine/lambda-labs/filesystems"
	"github.com/leptonai/lepton/machine/lambda-labs/instances"
	savetoken "github.com/leptonai/lepton/machine/lambda-labs/save-token"
	sshkeys "github.com/leptonai/lepton/machine/lambda-labs/ssh-keys"

	"github.com/spf13/cobra"
)

var (
	token     string
	tokenPath string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine lambda-labs" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "lambda-labs",
		Short:      "Implements lambda-labs sub-commands",
		Aliases:    []string{"lambda", "ll", "l"},
		SuggestFor: []string{"lambda", "ll", "l"},
	}

	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call (overwrites --token-path)")
	cmd.PersistentFlags().StringVarP(&tokenPath, "token-path", "p", common.DefaultTokenPath, "File path that contains the Lambda Labs API key token (to be overwritten by non-empty --token)")

	cmd.AddCommand(
		instances.NewCommand(),
		savetoken.NewCommand(),
		filesystems.NewCommand(),
		sshkeys.NewCommand(),
	)

	return cmd
}
