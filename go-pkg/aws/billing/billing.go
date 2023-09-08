// Package billing provides a client for AWS Billing API.
package billing

import (
	"context"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	costexplorer "github.com/aws/aws-sdk-go-v2/service/costexplorer"
	costexplorer_types "github.com/aws/aws-sdk-go-v2/service/costexplorer/types"
)

func GetCostAndUsage(ctx context.Context, cfg aws.Config, from, to time.Time, groupByDimensions []string, linkedAccounts []string, services []string, metrics []string) ([]costexplorer_types.ResultByTime, error) {
	cli := costexplorer.NewFromConfig(cfg)

	// group by clause
	groupBy := make([]costexplorer_types.GroupDefinition, 0)
	for _, d := range groupByDimensions {
		groupBy = append(groupBy, costexplorer_types.GroupDefinition{
			Type: costexplorer_types.GroupDefinitionTypeDimension,
			Key:  aws.String(d),
		})
	}

	// filter by account id
	var filterExpression *costexplorer_types.Expression

	// usage or credits
	recordTypeFilter := costexplorer_types.Expression{
		Dimensions: &costexplorer_types.DimensionValues{
			Key:    costexplorer_types.DimensionRecordType,
			Values: []string{"Usage"},
		},
	}

	andExpressions := []costexplorer_types.Expression{
		recordTypeFilter,
	}
	if len(linkedAccounts) != 0 {
		andExpressions = append(andExpressions, costexplorer_types.Expression{
			Dimensions: &costexplorer_types.DimensionValues{
				Key:    costexplorer_types.DimensionLinkedAccount,
				Values: linkedAccounts,
			},
		})
	}

	if len(services) != 0 {
		andExpressions = append(andExpressions, costexplorer_types.Expression{
			Dimensions: &costexplorer_types.DimensionValues{
				Key:    costexplorer_types.DimensionService,
				Values: services,
			},
		})
	}

	if len(andExpressions) == 1 {
		filterExpression = &andExpressions[0]
	} else {
		filterExpression = &costexplorer_types.Expression{
			And: andExpressions,
		}
	}

	t1, t2 := from.Format("2006-01-02"), to.Format("2006-01-02")
	resp, err := cli.GetCostAndUsage(ctx, &costexplorer.GetCostAndUsageInput{
		TimePeriod: &costexplorer_types.DateInterval{
			Start: &t1,
			End:   &t2,
		},
		Granularity: costexplorer_types.GranularityDaily,
		GroupBy:     groupBy,
		Metrics:     metrics,
		Filter:      filterExpression,
	})
	// Keeping the commented code in case we wanted to query which values are legit for
	// certain dimensions (not documented anywhere)
	// r, err := cli.GetDimensionValues(ctx, &costexplorer.GetDimensionValuesInput{
	// 	Dimension: costexplorer_types.DimensionServiceCode,
	// 	TimePeriod: &costexplorer_types.DateInterval{
	// 		Start: &t1,
	// 		End:   &t2,
	// 	},
	// })
	// for _, v := range r.DimensionValues {
	// 	fmt.Println(v.Attributes)
	// 	fmt.Println(*v.Value)
	// }

	if err != nil {
		return nil, err
	}

	return resp.ResultsByTime, nil
}
