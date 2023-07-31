// "mothership" controls the fleet of clusters
// to host lepton resources.
package main

import (
	"fmt"
	"os"

	"github.com/leptonai/lepton/mothership/cmd/mothership/aurora"
	"github.com/leptonai/lepton/mothership/cmd/mothership/clusters"
	"github.com/leptonai/lepton/mothership/cmd/mothership/contexts"
	"github.com/leptonai/lepton/mothership/cmd/mothership/kubeconfig"
	"github.com/leptonai/lepton/mothership/cmd/mothership/metering"
	"github.com/leptonai/lepton/mothership/cmd/mothership/purge"
	"github.com/leptonai/lepton/mothership/cmd/mothership/quotas"
	"github.com/leptonai/lepton/mothership/cmd/mothership/self"
	"github.com/leptonai/lepton/mothership/cmd/mothership/version"
	"github.com/leptonai/lepton/mothership/cmd/mothership/volumes"
	"github.com/leptonai/lepton/mothership/cmd/mothership/workspaces"

	"github.com/spf13/cobra"
)

const appName = "mothership"

var rootCmd = &cobra.Command{
	Use:        appName,
	Short:      "Lepton CLI for " + appName,
	SuggestFor: []string{"mothership"},
}

func init() {
	cobra.EnablePrefixMatching = true
}

func init() {
	rootCmd.AddCommand(
		aurora.NewCommand(),
		clusters.NewCommand(),
		contexts.NewCommand(),
		kubeconfig.NewCommand(),
		metering.NewCommand(),
		version.NewCommand(),
		workspaces.NewCommand(),
		quotas.NewCommand(),
		volumes.NewCommand(),
		purge.NewCommand(),
		self.NewCommand(),
	)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "%q failed %v\n", appName, err)
		os.Exit(1)
	}
	os.Exit(0)
}
