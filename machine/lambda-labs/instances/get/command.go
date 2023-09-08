// Package get implements get command.
package get

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

// NewCommand implements "machine lambda-labs instances get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "get [instance ID]",
		Short:      "Fetches a Lambda Labs instance information",
		Aliases:    []string{"get", "g", "fetch"},
		SuggestFor: []string{"get", "g", "fetch"},
		Run:        getFunc,
	}
	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
	if len(args) != 1 {
		slog.Error("no instance id -- requires 1 argument")
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

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	resp, _, err := apiClient.DefaultAPI.GetInstance(ctx, id).Execute()
	cancel()
	if err != nil {
		slog.Error("error getting an instance",
			"error", err,
		)
		os.Exit(1)
	}
	if err != nil {
		slog.Error("error deleting instance",
			"error", err,
		)
		os.Exit(1)
	}

	rss := make(common.Instances, 1)

	hostName := ""
	if resp.Data.Hostname.Get() != nil {
		hostName = *resp.Data.Hostname.Get()
	}
	rss[0] = common.Instance{
		ID:          resp.Data.Id,
		InstaceType: resp.Data.InstanceType.Name,
		Status:      resp.Data.Status,
		Region:      resp.Data.Region.Name,
		SSHKeys:     resp.Data.SshKeyNames,
		FileSystems: resp.Data.FileSystemNames,
		Hostname:    hostName,
	}
	fmt.Println(rss.String())
}
