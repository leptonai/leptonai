// Package billing provides a client for AWS Billing API.
package billing

import (
	"context"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	costexplorer "github.com/aws/aws-sdk-go-v2/service/costexplorer"
	costexplorer_types "github.com/aws/aws-sdk-go-v2/service/costexplorer/types"
)

func GetCostAndUsage(ctx context.Context, cfg aws.Config, from, to time.Time) ([]costexplorer_types.ResultByTime, error) {
	cli := costexplorer.NewFromConfig(cfg)

	t1, t2 := from.Format("2006-01-02"), to.Format("2006-01-02")
	resp, err := cli.GetCostAndUsage(ctx, &costexplorer.GetCostAndUsageInput{
		TimePeriod: &costexplorer_types.DateInterval{
			Start: &t1,
			End:   &t2,
		},
		Granularity: costexplorer_types.GranularityDaily,
		GroupBy: []costexplorer_types.GroupDefinition{
			{
				Type: costexplorer_types.GroupDefinitionTypeDimension,
				Key:  aws.String("SERVICE"),
			},
			{
				Type: costexplorer_types.GroupDefinitionTypeDimension,
				Key:  aws.String("USAGE_TYPE"),
			},
		},
		Metrics: []string{
			"BlendedCost",
		},
	})
	if err != nil {
		return nil, err
	}

	return resp.ResultsByTime, nil
}
