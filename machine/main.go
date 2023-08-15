// "machine" manages dev machines in Go.
package main

import (
	"fmt"
	"os"

	lambdalabs "github.com/leptonai/lepton/machine/lambda-labs"
	"github.com/spf13/cobra"
)

const appName = "machine"

var rootCmd = &cobra.Command{
	Use:        appName,
	Short:      "Lepton CLI for dev " + appName,
	SuggestFor: []string{"machine", "dev-machine"},
}

func init() {
	cobra.EnablePrefixMatching = true
}

func init() {
	rootCmd.AddCommand(
		lambdalabs.NewCommand(),
	)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "%q failed %v\n", appName, err)
		os.Exit(1)
	}
	os.Exit(0)
}
