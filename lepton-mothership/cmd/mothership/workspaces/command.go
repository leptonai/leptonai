// Package clusters implements clusters command.
package workspaces

import (
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/workspaces/create"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/workspaces/delete"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/workspaces/list"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/workspaces/logs"

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

// NewCommand implements "mothership workspaces" command.
// TODO: dedup with clusters/common.go
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "workspaces",
		Short: "Implements workspace sub-commands",
	}
	cmd.PersistentFlags().StringVarP(&mothershipURL, "mothership-url", "u", "https://mothership.cloud.lepton.ai/api/v1", "Mothership API endpoint URL")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call (overwrites --token-path)")
	cmd.PersistentFlags().StringVarP(&tokenPath, "token-path", "p", common.DefaultTokenPath, "File path that contains the beaer token for API call (to be overwritten by non-empty --token)")
	cmd.AddCommand(
		list.NewCommand(),
		create.NewCommand(),
		delete.NewCommand(),
		logs.NewCommand(),
	)
	return cmd
}
