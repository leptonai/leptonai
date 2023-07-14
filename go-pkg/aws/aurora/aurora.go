// package aurora implements aurora database utils
package aurora

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/rds/auth"
)

const (
	DefaultRegion        = "us-east-1"
	DefaultDriver        = "postgres"
	DefaultDBName        = "postgres"
	DefaultDBPort        = 5432
	DefaultAuthWithToken = false
)

var (
	homeDir, _        = os.UserHomeDir()
	DefaultAuroraPath = filepath.Join(homeDir, ".mothership", "aurora.json")
)

type AuroraConfig struct {
	Region        string
	DBDriverName  string
	DBName        string
	DBHost        string
	DBPort        int
	DBEndpoint    string
	DBUser        string
	DBPassword    string
	AuthWithToken bool
}

// Returns database source name (DSN) for the associated aurora database connection
func (c AuroraConfig) DSN() string {
	return fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s",
		c.DBHost, c.DBPort, c.DBUser, c.DBPassword, c.DBName,
	)
}

// Returns a DSN with the authToken in place of the password
func (c AuroraConfig) DSNWithAuthToken(authToken string) string {
	return fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s",
		c.DBHost, c.DBPort, c.DBUser, authToken, c.DBName,
	)
}

// NewHandler returns a new database handler to the aurora database specified in the config

// ref: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.IAMDBAuth.Connecting.Go.html
func NewHandler(auroraCfg AuroraConfig) (*sql.DB, error) {
	dsn := auroraCfg.DSN()
	if auroraCfg.AuthWithToken {
		awsCfg, err := config.LoadDefaultConfig(context.TODO())
		if err != nil {
			return nil, fmt.Errorf("NewHandler: configuration error: " + err.Error())
		}

		authTkn, err := auth.BuildAuthToken(
			context.TODO(), auroraCfg.DBEndpoint, auroraCfg.Region, auroraCfg.DBUser, awsCfg.Credentials)
		if err != nil {
			return nil, fmt.Errorf("NewHandler: failed to BuildAuthToken %v", err)
		}
		dsn = auroraCfg.DSNWithAuthToken(authTkn)
	}

	db, err := sql.Open(auroraCfg.DBDriverName, dsn)
	if err != nil {
		return nil, fmt.Errorf("NewHandler: failed to open database %v", err)
	}
	if err = db.Ping(); err != nil {
		return nil, fmt.Errorf("NewHandler: failed to ping database %v", err)
	}
	return db, nil
}

// ReplaceSQL replaces the instance occurrence of any string pattern with an increasing $n based sequence
func ReplaceSQL(old, pattern string) string {
	tmpCount := strings.Count(old, pattern)
	for m := 1; m <= tmpCount; m++ {
		old = strings.Replace(old, pattern, "$"+strconv.Itoa(m), 1)
	}
	return old
}
