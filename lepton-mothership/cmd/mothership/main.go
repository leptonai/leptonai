// "mothership" controls the fleet of clusters
// to host lepton resources.
package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/clusters"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/metering"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/token"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/version"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/workspaces"
)

const appName = "mothership"

var rootCmd = &cobra.Command{
	Use:        appName,
	Short:      "Lepton CLI for " + appName,
	SuggestFor: []string{"lepton-mothership"},
}

func init() {
	cobra.EnablePrefixMatching = true
}

func init() {
	rootCmd.AddCommand(
		clusters.NewCommand(),
		token.NewCommand(),
		metering.NewCommand(),
		version.NewCommand(),
		workspaces.NewCommand(),
	)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "%q failed %v\n", appName, err)
		os.Exit(1)
	}
	os.Exit(0)
}
