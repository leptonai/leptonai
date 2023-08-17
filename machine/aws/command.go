// Package: aws implements "aws" commands.
package aws

import (
	"github.com/leptonai/lepton/machine/aws/enis"
	"github.com/leptonai/lepton/machine/aws/secrets"
	vpcs_subnets "github.com/leptonai/lepton/machine/aws/vpcs-subnets"
	"github.com/leptonai/lepton/machine/aws/whoami"

	"github.com/spf13/cobra"
)

var (
	region string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "aws",
		Short:      "Implements aws sub-commands",
		Aliases:    []string{"a", "aw", "aa", "amazon"},
		SuggestFor: []string{"a", "aw", "aa", "amazon"},
	}

	cmd.PersistentFlags().StringVarP(&region, "region", "r", "us-east-1", "AWS region to send the API requests to")

	cmd.AddCommand(
		whoami.NewCommand(),
		vpcs_subnets.NewCommand(),
		secrets.NewCommand(),
		enis.NewCommand(),
	)

	return cmd
}
