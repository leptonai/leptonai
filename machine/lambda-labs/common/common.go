// Package common defines common lambda labs functions and variables.
package common

import (
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
)

var (
	homeDir, _               = os.UserHomeDir()
	DefaultTokenPath         = filepath.Join(homeDir, ".lambda-labs", "token")
	DefaultSSHPrivateKeyPath = filepath.Join(homeDir, ".lambda-labs", "ssh.private.pem")
	DefaultSSHPublicKeyPath  = filepath.Join(homeDir, ".lambda-labs", "ssh.public.pem")
)

func ReadToken(cmd *cobra.Command) (string, error) {
	tokenFlag := cmd.Flag("token")
	if tokenFlag != nil && tokenFlag.Value.String() != "" {
		// --token flag is not empty, so overwrites --token-path value
		return tokenFlag.Value.String(), nil
	}

	tokenPath := DefaultTokenPath
	tokenPathFlag := cmd.Flag("token-path")
	if tokenPathFlag != nil && tokenPathFlag.Value.String() != "" {
		tokenPath = tokenPathFlag.Value.String()
	}

	b, err := os.ReadFile(tokenPath)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func ReadTokenPath(cmd *cobra.Command) string {
	tokenPath := DefaultTokenPath
	tokenPathFlag := cmd.Flag("token-path")
	if tokenPathFlag != nil && tokenPathFlag.Value.String() != "" {
		tokenPath = tokenPathFlag.Value.String()
	}
	return tokenPath
}
