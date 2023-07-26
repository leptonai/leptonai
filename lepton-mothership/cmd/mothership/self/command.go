// Package self implements self command.
package self

import (
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/self/update"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/self/version"

	"github.com/spf13/cobra"
)

var (
	mothershipURL string
	token         string
	tokenPath     string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership self" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "self",
		Short: "Implements self sub-commands",
	}
	cmd.PersistentFlags().StringVarP(&mothershipURL, "mothership-url", "u", "", "Mothership API endpoint URL")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call (overwrites --token-path)")

	cmd.PersistentFlags().StringVarP(&tokenPath, "context-path", "p", common.DefaultContextPath, "Directory path that contains the context of the motership API call (to be overwritten by non-empty --token)")
	cmd.AddCommand(
		update.NewCommand(),
		version.NewCommand(),
	)
	return cmd
}
