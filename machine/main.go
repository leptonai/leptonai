// "machine" manages dev machines in Go.
package main

import (
	"fmt"
	"os"

	"github.com/leptonai/lepton/machine/aws"
	lambdalabs "github.com/leptonai/lepton/machine/lambda-labs"

	"github.com/spf13/cobra"
)

const appName = "machine"

var rootCmd = &cobra.Command{
	Use:        appName,
	Short:      "Lepton CLI for dev " + appName,
	Aliases:    []string{"machine", "mc", "m", "dev-machine"},
	SuggestFor: []string{"machine", "mc", "m", "dev-machine"},
}

func init() {
	cobra.EnablePrefixMatching = true
}

func init() {
	rootCmd.AddCommand(
		aws.NewCommand(),
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
