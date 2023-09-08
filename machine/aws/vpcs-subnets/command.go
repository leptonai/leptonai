// Package vpcssubnets implements vpcs-subnets command.
package vpcssubnets

import (
	"github.com/leptonai/lepton/machine/aws/vpcs-subnets/get"
	"github.com/leptonai/lepton/machine/aws/vpcs-subnets/ls"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws vpcs" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "vpcs-subnets",
		Short:      "VPC and subnets sub-commands",
		Aliases:    []string{"vpcs", "subnets", "subnet", "vpc", "vpc-subnets", "vpc-subnet", "vv", "vps", "vs", "v", "vss"},
		SuggestFor: []string{"vpcs", "subnets", "subnet", "vpc", "vpc-subnets", "vpc-subnet", "vv", "vps", "vs", "v", "vss"},
	}

	cmd.AddCommand(
		get.NewCommand(),
		ls.NewCommand(),
	)

	return cmd
}
