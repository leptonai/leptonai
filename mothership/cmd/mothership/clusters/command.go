// Package clusters implements clusters command.
package clusters

import (
	"github.com/leptonai/lepton/mothership/cmd/mothership/clusters/create"
	"github.com/leptonai/lepton/mothership/cmd/mothership/clusters/delete"
	"github.com/leptonai/lepton/mothership/cmd/mothership/clusters/get"
	inspect_eks "github.com/leptonai/lepton/mothership/cmd/mothership/clusters/inspect-eks"
	"github.com/leptonai/lepton/mothership/cmd/mothership/clusters/list"
	"github.com/leptonai/lepton/mothership/cmd/mothership/clusters/logs"
	"github.com/leptonai/lepton/mothership/cmd/mothership/clusters/services"
	"github.com/leptonai/lepton/mothership/cmd/mothership/clusters/update"
	"github.com/leptonai/lepton/mothership/cmd/mothership/clusters/wait"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"

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
		Use:        "clusters",
		Short:      "Implements clusters sub-commands",
		Aliases:    []string{"cluster", "cs", "c"},
		SuggestFor: []string{"cluster", "cs", "c"},
	}
	cmd.PersistentFlags().StringVarP(&mothershipURL, "mothership-url", "u", "", "Mothership API endpoint URL")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call (overwrites --token-path)")

	cmd.PersistentFlags().StringVarP(&tokenPath, "context-path", "p", common.DefaultContextPath, "Directory path that contains the context of the motership API call (to be overwritten by non-empty --token)")
	cmd.AddCommand(
		get.NewCommand(),
		list.NewCommand(),
		delete.NewCommand(),
		update.NewCommand(),
		inspect_eks.NewCommand(),
		logs.NewCommand(),
		services.NewCommand(),
		create.NewCommand(),
		wait.NewCommand(),
	)
	return cmd
}
