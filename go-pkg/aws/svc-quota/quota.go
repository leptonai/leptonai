package svcquota

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"sort"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
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

// Lists all service quotas for the service code.
// ref. https://docs.aws.amazon.com/servicequotas/2019-06-24/apireference/API_ListServiceQuotas.html
func ListServiceQuotas(ctx context.Context, cli *aws_svcquotas_v2.Client, svcCodes ...string) (Quotas, error) {
	log.Printf("listing service quota for %q", svcCodes)
	quotas := make([]Quota, 0)
	for _, svcCode := range svcCodes {
		var nextToken *string = nil
		for i := 0; i < 10; i++ {
			out, err := cli.ListServiceQuotas(ctx, &aws_svcquotas_v2.ListServiceQuotasInput{
				ServiceCode: &svcCode,
				NextToken:   nextToken,
			})
			if err != nil {
				return nil, err
			}

			for _, q := range out.Quotas {
				quotas = append(quotas, Quota{
					QuotaCode:   *q.QuotaCode,
					ServiceCode: svcCode,
					QuotaName:   *q.QuotaName,
					Value:       *q.Value})
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
	QuotaCode   string  `json:"quota-code"`
	ServiceCode string  `json:"service-code"`
	QuotaName   string  `json:"quota-name"`
	Value       float64 `json:"value"`
}

type Quotas []Quota

func (qs Quotas) String() string {
	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader([]string{"QUOTA CODE", "SERVICE CODE", "QUOTA NAME", "VALUE"})
	for _, q := range qs {
		tb.Append([]string{q.QuotaCode, q.ServiceCode, q.QuotaName, fmt.Sprintf("%.5f", q.Value)})
	}
	tb.Render()
	return buf.String()
}
