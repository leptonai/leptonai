// Package ls implements ls command.
package ls

import (
	"context"
	"fmt"
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

// NewCommand implements "machine lambda-labs ssh-keys ls" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "ls",
		Short:      "Lists Lambda Labs SSH keys",
		Aliases:    []string{"list", "l"},
		SuggestFor: []string{"list", "l"},
		Run:        lsFunc,
	}
	return cmd
}

func lsFunc(cmd *cobra.Command, args []string) {
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

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	resp, _, err := apiClient.DefaultAPI.ListSSHKeys(ctx).Execute()
	cancel()
	if err != nil {
		slog.Error("error listing ssh keys",
			"error", err,
		)
		os.Exit(1)
	}

	if len(resp.Data) == 0 {
		slog.Info("no instance found")
		return
	}

	rss := make(common.SSHKeys, 0, len(resp.Data))
	for _, d := range resp.Data {
		rss = append(rss, common.SSHKey{
			ID:   d.Id,
			Name: d.Name,
		})
	}
	fmt.Println(rss.String())
}
