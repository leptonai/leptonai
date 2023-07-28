// Package ping implements ping command.
package ping

import (
	"context"
	"database/sql"
	"log"
	"time"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/rds/auth"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	_ "github.com/lib/pq"
	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership aurora ping" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "ping",
		Short: "Pings the AWS aurora database",
		Run:   pingFunc,
	}
	return cmd
}

// ref. https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.IAMDBAuth.Connecting.Go.html#UsingWithRDS.IAMDBAuth.Connecting.GoV2
func pingFunc(cmd *cobra.Command, args []string) {
	auroraCfg := common.ReadAuroraConfigFromFlag(cmd)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	dsn := auroraCfg.DSN()
	if auroraCfg.AuthWithToken {
		log.Printf("--auth-with-token specified, ignoring --db-password")

		awsCfg, err := config.LoadDefaultConfig(ctx)
		if err != nil {
			panic("configuration error: " + err.Error())
		}

		authTkn, err := auth.BuildAuthToken(
			ctx, auroraCfg.DBEndpoint, auroraCfg.Region, auroraCfg.DBUser, awsCfg.Credentials)
		if err != nil {
			log.Fatalf("failed to BuildAuthToken %v", err)
		}
		dsn = auroraCfg.DSNWithAuthToken(authTkn)
	}

	db, err := sql.Open(auroraCfg.DBDriverName, dsn)
	if err != nil {
		log.Fatal(err)
	}

	now := time.Now()
	log.Printf("ping...")
	if err = db.Ping(); err != nil {
		panic(err)
	}
	log.Printf("ping took %v", time.Since(now))
}
