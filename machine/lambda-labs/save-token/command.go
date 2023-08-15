// Package savetoken implements save-token command.
package savetoken

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/leptonai/lepton/machine/lambda-labs/common"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine lambda-labs save-token" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "save-token",
		Short:      "Saves a token to a file",
		Aliases:    []string{"savetoken", "save", "token"},
		SuggestFor: []string{"savetoken", "save", "token"},
		Run:        saveTokenFunc,
	}
	return cmd
}

func saveTokenFunc(cmd *cobra.Command, args []string) {
	if len(args) != 1 {
		slog.Error("expected 1 argument for token")
		return
	}

	token := args[0]
	tokenPath := common.ReadTokenPath(cmd)

	if err := os.MkdirAll(filepath.Dir(tokenPath), 0755); err != nil {
		slog.Error("error creating directory",
			"directory", filepath.Dir(tokenPath),
			"error", err,
		)
		return
	}

	if err := os.WriteFile(tokenPath, []byte(token), 0644); err != nil {
		slog.Error("error writing token",
			"file", tokenPath,
			"error", err,
		)
		return
	}

	slog.Info("token saved successfully",
		"file", tokenPath,
	)

	fmt.Printf("\ncat %s\n\n", tokenPath)
}
