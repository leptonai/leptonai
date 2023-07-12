package common

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"

	"github.com/spf13/cobra"
)

var (
	homeDir, _       = os.UserHomeDir()
	DefaultTokenPath = filepath.Join(homeDir, ".mothership", "token")
)

func ReadTokenFromFlag(cmd *cobra.Command) string {
	tokenFlag := cmd.Flag("token")
	tokenPathFlag := cmd.Flag("token-path")

	token := ""
	if tokenFlag != nil && tokenFlag.Value.String() != "" {
		// --token flag is not empty, so overwrites --token-path value
		token = tokenFlag.Value.String()
	}

	if token == "" {
		// --token flag is empty, so fallback to --token-path value
		// assume the default flag value is set to "DefaultTokenPath"
		// so this is never an empty string
		if tokenPathFlag == nil || tokenPathFlag.Value.String() == "" {
			log.Fatal("both --token and --token-path are empty")
		}

		tokenPath := tokenPathFlag.Value.String()
		b, err := os.ReadFile(tokenPath)
		if err != nil {
			log.Fatalf("failed to read token file %v", err)
		}

		token = string(b)
	}

	if token == "" {
		log.Fatal("no token found")
	}

	return token
}

func ReadMothershipURLFromFlag(cmd *cobra.Command) string {
	return cmd.Flag("mothership-url").Value.String()
}

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

func ReadAuroraConfigFromFlag(cmd *cobra.Command) AuroraConfig {
	dbHost := cmd.Flag("db-host").Value.String()
	dbPort, _ := strconv.Atoi(cmd.Flag("db-port").Value.String())

	s := cmd.Flag("auth-with-token").Value.String()
	authWithToken, _ := strconv.ParseBool(s)

	return AuroraConfig{
		Region:        cmd.Flag("region").Value.String(),
		DBDriverName:  cmd.Flag("db-driver-name").Value.String(),
		DBName:        cmd.Flag("db-name").Value.String(),
		DBHost:        dbHost,
		DBPort:        dbPort,
		DBEndpoint:    fmt.Sprintf("%s:%d", dbHost, dbPort),
		DBUser:        cmd.Flag("db-user").Value.String(),
		DBPassword:    cmd.Flag("db-password").Value.String(),
		AuthWithToken: authWithToken,
	}
}

func (c AuroraConfig) DSN() string {
	return fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s",
		c.DBHost, c.DBPort, c.DBUser, c.DBPassword, c.DBName,
	)
}

func (c AuroraConfig) DSNWithAuthToken(authToken string) string {
	return fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s",
		c.DBHost, c.DBPort, c.DBUser, authToken, c.DBName,
	)
}
