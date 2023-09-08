// Package kubeconfig implements kubeconfig command.
package kubeconfig

import (
	update_all "github.com/leptonai/lepton/mothership/cmd/mothership/kubeconfig/update-all"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters kubeconfig" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "kubeconfig",
		Short:      "Implements kubeconfig sub-commands",
		Aliases:    []string{"kcfg", "k"},
		SuggestFor: []string{"kcfg", "k"},
	}
	cmd.AddCommand(
		update_all.NewCommand(),
	)
	return cmd
}
