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

// NewCommand implements "machine lambda-labs instances ls" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "ls",
		Short:      "Lists Lambda Labs instances",
		Aliases:    []string{"list"},
		SuggestFor: []string{"list"},
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
	resp, _, err := apiClient.DefaultAPI.ListInstances(ctx).Execute()
	cancel()
	if err != nil {
		slog.Error("error listing instances",
			"error", err,
		)
		os.Exit(1)
	}

	if len(resp.Data) == 0 {
		slog.Info("no instance found")
		return
	}

	rss := make(common.Instances, 0, len(resp.Data))
	for _, inst := range resp.Data {
		hostName := ""
		if inst.Hostname.Get() != nil {
			hostName = *inst.Hostname.Get()
		}
		rss = append(rss, common.Instance{
			ID:          inst.Id,
			InstaceType: inst.InstanceType.Name,
			Status:      inst.Status,
			Region:      inst.Region.Name,
			SSHKeys:     inst.SshKeyNames,
			FileSystems: inst.FileSystemNames,
			Hostname:    hostName,
		})
	}
	fmt.Println(rss.String())
}
