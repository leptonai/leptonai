// Package common defines common lambda labs functions and variables.
package common

import (
	"errors"

	"github.com/spf13/cobra"
)

func ReadRegion(cmd *cobra.Command) (string, error) {
	regionFlag := cmd.Flag("region")
	if regionFlag != nil && regionFlag.Value.String() != "" {
		// --token flag is not empty, so overwrites --token-path value
		return regionFlag.Value.String(), nil
	}
	return "", errors.New("region flag is empty")
}
