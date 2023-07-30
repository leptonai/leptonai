// Package metering implements metering command.
package metering

import (
	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/go-pkg/aws/aurora"
	"github.com/leptonai/lepton/mothership/cmd/mothership/metering/aggregate"
	"github.com/leptonai/lepton/mothership/cmd/mothership/metering/backfill"
	"github.com/leptonai/lepton/mothership/cmd/mothership/metering/get"
	"github.com/leptonai/lepton/mothership/cmd/mothership/metering/sync"
)

var (
	dbDriverName  string
	dbRegion      string
	dbHost        string
	dbName        string
	dbPort        int
	dbUser        string
	dbPassword    string
	authWithToken bool

	auroraConfig     bool
	auroraConfigPath string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership metering" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "metering",
		Short: "Prints out Lepton metering",
	}

	// aurora db related flags
	cmd.PersistentFlags().StringVarP(&dbDriverName, "db-driver-name", "", aurora.DefaultDriver, "AWS Aurora database driver name")
	cmd.PersistentFlags().StringVarP(&dbName, "db-name", "", aurora.DefaultDBName, "AWS Aurora database name")
	cmd.PersistentFlags().StringVar(&dbHost, "db-host", "", "AWS Aurora database host")
	cmd.PersistentFlags().StringVar(&dbRegion, "db-region", "us-east-1", "AWS Aurora database region")
	cmd.PersistentFlags().IntVarP(&dbPort, "db-port", "", aurora.DefaultDBPort, "AWS Aurora database port")

	cmd.PersistentFlags().StringVar(&dbUser, "db-user", "", "AWS Aurora database user")
	cmd.PersistentFlags().StringVar(&dbPassword, "db-password", "", "AWS Aurora database password")
	cmd.PersistentFlags().BoolVar(&authWithToken, "auth-with-token", aurora.DefaultAuthWithToken, "Authenticate with token, overwrites AWS Aurora database password, user name must be valid")
	cmd.PersistentFlags().BoolVar(&auroraConfig, "aurora-config", false, "use stored Aurora DB config")
	cmd.PersistentFlags().StringVar(&auroraConfigPath, "aurora-config-path", aurora.DefaultAuroraPath, "Aurora DB config file path")

	cmd.AddCommand(get.NewCommand())
	cmd.AddCommand(sync.NewCommand())
	cmd.AddCommand(aggregate.NewCommand())
	cmd.AddCommand(backfill.NewCommand())
	return cmd
}
