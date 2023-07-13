// Package version implements version command.
package version

import (
	"fmt"

	"github.com/leptonai/lepton/go-pkg/version"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership version" command.
func NewCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "version",
		Short: "Prints out Lepton version",
		Run:   versionFunc,
	}
}

func versionFunc(cmd *cobra.Command, args []string) {
	fmt.Printf("%+v", version.VersionInfo)
}
