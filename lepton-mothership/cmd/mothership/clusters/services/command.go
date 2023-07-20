// Package services implements services command.
package services

import (
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/services/get"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/services/list"
	portforward "github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters/services/port-forward"

	"github.com/spf13/cobra"
)

var (
	kubeconfigPath string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters services" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "services",
		Short:      "Implements services sub-commands",
		SuggestFor: []string{"svcs"},
	}
	cmd.PersistentFlags().StringVarP(&kubeconfigPath, "kubeconfig", "k", "", "Kubeconfig path (otherwise, client uses the one from KUBECONFIG env var)")
	cmd.AddCommand(
		list.NewCommand(),
		get.NewCommand(),
		portforward.NewCommand(),
	)
	return cmd
}
