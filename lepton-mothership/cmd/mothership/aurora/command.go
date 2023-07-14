// Package aurora implements aurora command.
package aurora

import (
	"github.com/leptonai/lepton/go-pkg/aws/aurora"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/aurora/config"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/aurora/ping"

	"github.com/spf13/cobra"
)

var (
	region        string
	dbDriverName  string
	dbName        string
	dbHost        string
	dbPort        int
	dbUser        string
	dbPassword    string
	authWithToken bool
	auroraConfig  bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership aurora" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "aurora",
		Short: "aurora sub-commands",
	}

	cmd.PersistentFlags().StringVarP(&region, "region", "r", aurora.DefaultRegion, "AWS region hosting the AWS Aurora database")

	cmd.PersistentFlags().StringVarP(&dbDriverName, "db-driver-name", "d", aurora.DefaultDriver, "AWS Aurora database driver name")
	cmd.PersistentFlags().StringVarP(&dbName, "db-name", "n", aurora.DefaultDBName, "AWS Aurora database name")
	cmd.PersistentFlags().StringVar(&dbHost, "db-host", "", "AWS Aurora database host")
	cmd.PersistentFlags().IntVarP(&dbPort, "db-port", "p", aurora.DefaultDBPort, "AWS Aurora database port")

	cmd.PersistentFlags().StringVar(&dbUser, "db-user", "", "AWS Aurora database user")
	cmd.PersistentFlags().StringVar(&dbPassword, "db-password", "", "AWS Aurora database password")
	cmd.PersistentFlags().BoolVar(&authWithToken, "auth-aurora-with-token", aurora.DefaultAuthWithToken, "Authenticate with token, overwrites AWS Aurora database password, user name must be valid")
	cmd.PersistentFlags().BoolVar(&auroraConfig, "aurora-config", false, "use stored Aurora DB config")
	cmd.AddCommand(ping.NewCommand())
	cmd.AddCommand(config.NewCommand())

	return cmd
}
