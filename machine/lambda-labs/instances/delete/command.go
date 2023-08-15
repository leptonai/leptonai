// Package delete implements delete command.
package delete

import (
	"fmt"
	"log/slog"
	"os"

	openapiclient "github.com/leptonai/lepton/go-pkg/openapi/lambdalabs"
	"github.com/leptonai/lepton/machine/lambda-labs/common"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine lambda-labs instances delete" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "delete [instance ID]",
		Short:      "Deletes a Lambda Labs instance",
		Aliases:    []string{"del", "d"},
		SuggestFor: []string{"del", "d"},
		Run:        deleteFunc,
	}
	return cmd
}

func deleteFunc(cmd *cobra.Command, args []string) {
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

	slog.Info("deleting instance", "id", id)
	resp, _, err := apiClient.DefaultAPI.
		TerminateInstanceExecute(
			openapiclient.ApiTerminateInstanceRequest{}.
				TerminateInstanceRequest(openapiclient.TerminateInstanceRequest{
					InstanceIds: []string{id},
				}),
		)
	if err != nil {
		slog.Error("error deleting instance",
			"error", err,
		)
		os.Exit(1)
	}

	if len(resp.Data.TerminatedInstances) != 1 {
		slog.Error(
			"expected only 1 terminated instance",
			"terminated-instances", len(resp.Data.TerminatedInstances),
		)
		os.Exit(1)
	}

	rss := make(common.Instances, 0, len(resp.Data.TerminatedInstances))
	for _, inst := range resp.Data.TerminatedInstances {
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

	fmt.Println("terminated the following:")
	fmt.Println(rss.String())
}
