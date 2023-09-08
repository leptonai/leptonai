// Package types implements types command.
package types

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

// NewCommand implements "machine lambda-labs instances types" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "types",
		Short:      "Lists Lambda Labs instance types",
		Aliases:    []string{"type", "ts", "t", "tss"},
		SuggestFor: []string{"type", "ts", "t", "tss"},
		Run:        typesFunc,
	}
	return cmd
}

func typesFunc(cmd *cobra.Command, args []string) {
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
	resp, _, err := apiClient.DefaultAPI.InstanceTypes(ctx).Execute()
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

	rss := make(common.InstanceTypes, 0, len(resp.Data))
	for _, inst := range resp.Data {
		regions := make([]string, 0)
		for _, r := range inst.RegionsWithCapacityAvailable {
			regions = append(regions, fmt.Sprintf("%s (%s)", r.Name, r.Description))
		}
		reg := []string{"all"}
		if len(regions) > 0 {
			reg = regions
		}
		rss = append(rss, common.InstanceType{
			Name:            inst.InstanceType.Name,
			Description:     inst.InstanceType.Description,
			Regions:         reg,
			PriceUSDPerHour: float64(inst.InstanceType.PriceCentsPerHour) / 100.0,
			VCPU:            inst.InstanceType.Specs.Vcpus,
			RAMGiB:          inst.InstanceType.Specs.MemoryGib,
			StorageGiB:      inst.InstanceType.Specs.StorageGib,
		})
	}
	fmt.Println(rss.String())
}
