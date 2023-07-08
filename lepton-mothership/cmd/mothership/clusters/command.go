// Package clusters implements clusters command.
package clusters

import (
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/create"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/delete"
	inspect_eks "github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/inspect-eks"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/list"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/logs"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/update"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/wait"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"

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

// NewCommand implements "mothership clusters" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "clusters",
		Short: "Implements clusters sub-commands",
	}
	cmd.PersistentFlags().StringVarP(&mothershipURL, "mothership-url", "u", "https://mothership.cloud.lepton.ai/api/v1/clusters", "Mothership API endpoint URL")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call (overwrites --token-path)")
	cmd.PersistentFlags().StringVarP(&tokenPath, "token-path", "p", common.DefaultTokenPath, "File path that contains the beaer token for API call (to be overwritten by non-empty --token)")
	cmd.AddCommand(
		list.NewCommand(),
		delete.NewCommand(),
		update.NewCommand(),
		inspect_eks.NewCommand(),
		logs.NewCommand(),
		create.NewCommand(),
		wait.NewCommand(),
	)
	return cmd
}
