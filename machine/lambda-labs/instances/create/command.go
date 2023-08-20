// Package create implements create command.
package create

import (
	"log/slog"
	"os"

	openapiclient "github.com/leptonai/lepton/go-pkg/openapi/lambdalabs"
	"github.com/leptonai/lepton/machine/lambda-labs/common"

	"github.com/spf13/cobra"
)

var (
	name            string
	region          string
	instanceType    string
	sshKeyNames     []string
	filesystemNames []string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine lambda-labs instances create" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "create",
		Short:      "Creates a Lambda Labs instance",
		Aliases:    []string{"add", "a", "creates", "c", "launch", "apply"},
		SuggestFor: []string{"add", "a", "creates", "c", "launch", "apply"},
		Run:        createFunc,
	}

	cmd.PersistentFlags().StringVar(&name, "name", "", "Required name of the instance to launch")
	cmd.PersistentFlags().StringVar(&region, "region", "", "Required region to launch an instance")
	cmd.PersistentFlags().StringVar(&instanceType, "instance-type", "", "Required instance type name to launch")
	cmd.PersistentFlags().StringSliceVar(&sshKeyNames, "ssh-key-names", nil, "Required SSH key names (comma-separated)")
	cmd.PersistentFlags().StringSliceVar(&filesystemNames, "filesystem-names", nil, "Optional filesystem names (comma-separated)")

	return cmd
}

func createFunc(cmd *cobra.Command, args []string) {
	if len(name) == 0 {
		slog.Error("no instance name")
		os.Exit(1)
	}
	if len(region) == 0 {
		slog.Error("no region found")
		os.Exit(1)
	}
	if len(instanceType) == 0 {
		slog.Error("no instance type found")
		os.Exit(1)
	}
	if len(sshKeyNames) == 0 {
		slog.Error("no ssh key name found")
		os.Exit(1)
	}

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

	quantity := int32(1)
	resp, _, err := apiClient.DefaultAPI.
		LaunchInstanceExecute(
			openapiclient.ApiLaunchInstanceRequest{}.
				LaunchInstanceRequest(openapiclient.LaunchInstanceRequest{
					Name:             *openapiclient.NewNullableString(&name),
					RegionName:       region,
					InstanceTypeName: instanceType,
					SshKeyNames:      sshKeyNames,
					FileSystemNames:  filesystemNames,
					Quantity:         &quantity,
				}),
		)
	if err != nil {
		slog.Error("error creating instance",
			"error", err,
		)
		os.Exit(1)
	}
	iss := resp.Data.GetInstanceIds()
	if len(iss) != 1 {
		slog.Error(
			"expected only 1 instance ID",
			"instance-ids", iss,
		)
		os.Exit(1)
	}

	instanceID := iss[0]

	slog.Info("successfully created instance",
		"instance-id", instanceID,
	)
}
