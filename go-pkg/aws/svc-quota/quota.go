package svcquota

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"sort"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/cloudwatch"
	"github.com/aws/aws-sdk-go-v2/service/cloudwatch/types"
	aws_svcquotas_v2 "github.com/aws/aws-sdk-go-v2/service/servicequotas"
	aws_svcquotas_v2_types "github.com/aws/aws-sdk-go-v2/service/servicequotas/types"
	"github.com/olekukonko/tablewriter"
)

const listInterval = 3 * time.Second

// Lists all services.
// ref. https://docs.aws.amazon.com/servicequotas/2019-06-24/apireference/API_ListServices.html
func ListServices(ctx context.Context, cfg aws.Config) ([]aws_svcquotas_v2_types.ServiceInfo, error) {
	svcs := make([]aws_svcquotas_v2_types.ServiceInfo, 0)
	cli := aws_svcquotas_v2.NewFromConfig(cfg)

	var nextToken *string = nil
	for i := 0; i < 10; i++ {
		out, err := cli.ListServices(ctx, &aws_svcquotas_v2.ListServicesInput{
			NextToken: nextToken,
		})
		if err != nil {
			return nil, err
		}

		svcs = append(svcs, out.Services...)

		nextToken = out.NextToken
		if nextToken == nil {
			// no more resources are available
			break
		}

		log.Printf("listed %d services so far", len(svcs))
		time.Sleep(listInterval)
	}
	return svcs, nil
}

func getUsageString(u *aws_svcquotas_v2_types.MetricInfo) string {
	if u == nil {
		return "empty"
	}
	ret := ""
	if u.MetricDimensions != nil {
		for k, v := range u.MetricDimensions {
			ret += "[" + k + "," + v + "] "
		}
	}
	if u.MetricName != nil {
		ret += "name: " + *u.MetricName
	}

	if u.MetricNamespace != nil {
		ret += "ns: " + *u.MetricNamespace
	}
	return ret
}

func getDimensions(dimensions map[string]string) []types.Dimension {
	ret := make([]types.Dimension, 0)
	for k, v := range dimensions {
		key := k
		value := v
		dimension := types.Dimension{
			Name:  &key,
			Value: &value,
		}
		ret = append(ret, dimension)
	}

	return ret
}

func queryUsageMetrics(client *cloudwatch.Client, ctx context.Context, u *aws_svcquotas_v2_types.MetricInfo) *float64 {
	if u == nil || u.MetricName == nil || u.MetricNamespace == nil {
		return nil
	}
	period := int32(30)
	endTime := time.Now()
	startTime := endTime.Add(-time.Minute * 10)
	request := &cloudwatch.GetMetricStatisticsInput{
		Dimensions: getDimensions(u.MetricDimensions),
		MetricName: u.MetricName,
		Namespace:  u.MetricNamespace,
		Period:     &period, // data granularity in seconds
		StartTime:  &startTime,
		EndTime:    &endTime,
		Statistics: []types.Statistic{types.Statistic("Maximum")},
	}

	output, err := client.GetMetricStatistics(ctx, request)
	if err != nil || output == nil {
		log.Printf("failed to get usage metric or output is nil, %s: %s\n", err, getUsageString(u))
		return nil
	}

	if len(output.Datapoints) == 0 {
		return nil
	}

	return output.Datapoints[0].Maximum
}

func ListImportantQuotas(ctx context.Context, cli *aws_svcquotas_v2.Client, cwClient *cloudwatch.Client, quotaCodeList map[string][]string) (Quotas, error) {
	log.Printf("getting service quota")
	quotas := make([]Quota, 0)
	for serviceCode, quotaCodes := range quotaCodeList {
		for _, quotaCode := range quotaCodes {
			q := aws_svcquotas_v2_types.ServiceQuota{}
			out, err := cli.GetServiceQuota(ctx, &aws_svcquotas_v2.GetServiceQuotaInput{
				QuotaCode:   &quotaCode,
				ServiceCode: &serviceCode,
			})

			// to work around weird behavior of aws quota api: e.g. for S3 buckets, if there has been no quota updates before,
			// then GetServiceQuota will return "quota and service do not exist" error, but GetAWSDefaultServiceQuota can return
			// data. This is due to differences in "applied quota" and "default quota" concepts
			defaultApiOut, defaulApiErr := cli.GetAWSDefaultServiceQuota(ctx, &aws_svcquotas_v2.GetAWSDefaultServiceQuotaInput{
				QuotaCode:   &quotaCode,
				ServiceCode: &serviceCode,
			})
			if err != nil {
				if strings.Contains(err.Error(), "quota and service do not exist") && defaulApiErr == nil {
					q = *defaultApiOut.Quota
				} else {
					return nil, fmt.Errorf("quota code %s, service code %s: %w", quotaCode, serviceCode, err)
				}
			} else {
				q = *out.Quota
			}
			usage := queryUsageMetrics(cwClient, ctx, q.UsageMetric)
			utilization := float64(0)
			if usage != nil {
				utilization = *usage / *q.Value
			}
			quotas = append(quotas, Quota{
				QuotaCode:   quotaCode,
				ServiceCode: serviceCode,
				QuotaName:   *q.QuotaName,
				Value:       *q.Value,
				Usage:       usage,
				Utilization: utilization})
		}
	}
	return quotas, nil
}

// Lists all service quotas for the service code.
// ref. https://docs.aws.amazon.com/servicequotas/2019-06-24/apireference/API_ListServiceQuotas.html
func ListServiceQuotas(ctx context.Context, cli *aws_svcquotas_v2.Client, cwClient *cloudwatch.Client, svcCodes ...string) (Quotas, error) {
	log.Printf("listing service quota for %q", svcCodes)
	quotas := make([]Quota, 0)

	maxResult := int32(80)
	for _, svcCode := range svcCodes {
		var nextToken *string = nil
		for i := 0; i < 10; i++ {
			out, err := cli.ListServiceQuotas(ctx, &aws_svcquotas_v2.ListServiceQuotasInput{
				ServiceCode: &svcCode,
				NextToken:   nextToken,
				MaxResults:  &maxResult,
			})
			if err != nil {
				return nil, err
			}

			for _, q := range out.Quotas {
				usage := queryUsageMetrics(cwClient, ctx, q.UsageMetric)
				utilization := float64(0)
				if usage != nil {
					utilization = *usage / *q.Value
				}
				quotas = append(quotas, Quota{
					QuotaCode:   *q.QuotaCode,
					ServiceCode: svcCode,
					QuotaName:   *q.QuotaName,
					Value:       *q.Value,
					Usage:       usage,
					Utilization: utilization})
			}

			nextToken = out.NextToken
			if nextToken == nil {
				// no more resources are available
				break
			}

			log.Printf("listed %d quotas so far for %q", len(quotas), svcCode)
			time.Sleep(listInterval)
		}
	}

	sort.SliceStable(quotas, func(i, j int) bool {
		if quotas[i].ServiceCode == quotas[j].ServiceCode {
			return quotas[i].QuotaName < quotas[j].QuotaName
		}
		return quotas[i].ServiceCode < quotas[j].ServiceCode
	})
	return quotas, nil
}

type Quota struct {
	QuotaCode   string   `json:"quota-code"`
	ServiceCode string   `json:"service-code"`
	QuotaName   string   `json:"quota-name"`
	Value       float64  `json:"value"`
	Usage       *float64 `json:"usage"`
	Utilization float64  `json:"utilization"`
}

type Quotas []Quota

func (qs Quotas) String() string {
	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader([]string{"QUOTA CODE", "SERVICE CODE", "QUOTA NAME", "VALUE", "USAGE", "UTILIZATION"})
	for _, q := range qs {
		usage := "n/a"
		if q.Usage != nil {
			usage = fmt.Sprintf("%.5f", *q.Usage)
		}
		tb.Append([]string{q.QuotaCode, q.ServiceCode, q.QuotaName, fmt.Sprintf("%.5f", q.Value), usage, fmt.Sprintf("%.2f%%", 100*q.Utilization)})
	}
	tb.Render()
	return buf.String()
}
