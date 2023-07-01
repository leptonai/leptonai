package common

import (
	"log"
	"os"
	"path/filepath"

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
		log.Printf("empty --token, fallback to token-path %q", tokenPath)
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
