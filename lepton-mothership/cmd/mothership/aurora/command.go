// Package aurora implements aurora command.
package aurora

import (
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

	cmd.PersistentFlags().StringVarP(&region, "region", "r", "us-east-1", "AWS region hosting the AWS Aurora database")

	cmd.PersistentFlags().StringVarP(&dbDriverName, "db-driver-name", "d", "postgres", "AWS Aurora database driver name")
	cmd.PersistentFlags().StringVarP(&dbName, "db-name", "n", "postgres", "AWS Aurora database name")
	cmd.PersistentFlags().StringVar(&dbHost, "db-host", "", "AWS Aurora database host")
	cmd.PersistentFlags().IntVarP(&dbPort, "db-port", "p", 5432, "AWS Aurora database port")

	cmd.PersistentFlags().StringVar(&dbUser, "db-user", "", "AWS Aurora database user")
	cmd.PersistentFlags().StringVar(&dbPassword, "db-password", "", "AWS Aurora database password")
	cmd.PersistentFlags().BoolVar(&authWithToken, "auth-with-token", false, "Authenticate with token, overwrites AWS Aurora database password, user name must be valid")

	cmd.AddCommand(ping.NewCommand())

	return cmd
}
