// Package awsauth implements awsauth command.
package awsauth

import (
	addrole "github.com/leptonai/lepton/machine/aws/eks/aws-auth/add-role"
	"github.com/leptonai/lepton/machine/aws/eks/aws-auth/get"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws eks aws-auth" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "aws-auth",
		Short:      "Implements aws-auth sub-commands",
		Aliases:    []string{"awsauth", "a", "auth", "aws-auth-configmap"},
		SuggestFor: []string{"awsauth", "a", "auth", "aws-auth-configmap"},
	}

	cmd.AddCommand(
		addrole.NewCommand(),
		get.NewCommand(),
	)
	return cmd
}
