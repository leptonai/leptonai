// Package delete implements delete command.
package delete

import (
	"context"
	"log/slog"
	"os"
	"time"

	openapiclient "github.com/leptonai/lepton/go-pkg/openapi/lambdalabs"
	"github.com/leptonai/lepton/machine/lambda-labs/common"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine lambda-labs ssh-keys delete" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "delete [SSH KEY ID]",
		Short:      "Deletes a Lambda Labs SSH key",
		Aliases:    []string{"del", "d"},
		SuggestFor: []string{"del", "d"},
		Run:        deleteFunc,
	}
	return cmd
}

func deleteFunc(cmd *cobra.Command, args []string) {
	if len(args) != 1 {
		slog.Error("no key id -- requires 1 argument")
		os.Exit(1)
	}
	id := args[0]

	token, err := common.ReadToken(cmd)
	if err != nil {
		slog.Error("error reading token",
			"error", err,
		)
		os.Exit(1)
	}

	configuration := openapiclient.NewConfiguration()
	configuration.DefaultHeader["Authorization"] = "Bearer " + token
	apiClient := openapiclient.NewAPIClient(configuration)

	slog.Info("deleting ssh key", "id", id)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	httpResp, err := apiClient.DefaultAPI.DeleteSSHKey(ctx, id).Execute()
	cancel()
	if err != nil {
		slog.Error("error deleting ssh key",
			"error", err,
		)
		os.Exit(1)
	}

	if httpResp.StatusCode >= 400 {
		slog.Error("failed to delete ssh key",
			"id", id,
			"status", httpResp.Status,
			"status-code", httpResp.StatusCode,
		)
		os.Exit(1)
	}

	slog.Info("successfully deleted ssh key",
		"id", id,
		"status", httpResp.Status,
		"status-code", httpResp.StatusCode,
	)
}
