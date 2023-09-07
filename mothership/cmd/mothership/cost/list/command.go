// Package list implements list command.
package list

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"sort"
	"strconv"
	"strings"
	"time"

	costexplorer_types "github.com/aws/aws-sdk-go-v2/service/costexplorer/types"
	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/billing"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
	"golang.org/x/exp/constraints"
)

var (
	accounts    string
	region      string
	computeOnly bool

	fromDate string
	toDate   string

	fromTime time.Time
	toTime   time.Time
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all spendings",
		Run:   listFunc,
	}
	cmd.PersistentFlags().StringVarP(&accounts, "accounts", "a", "", "AWS accounts to query, separated by comma; leave empty to query all linked accounts")
	cmd.PersistentFlags().StringVarP(&region, "region", "r", "us-east-1", "AWS API region to query, includes all regions cost")
	cmd.PersistentFlags().BoolVarP(&computeOnly, "compute-only", "c", false, "Only print ec2-related costs")

	cmd.PersistentFlags().StringVarP(&fromDate, "from", "", "", "From date, in UTC; in format 2006-01-02")
	cmd.PersistentFlags().StringVarP(&toDate, "to", "", "", "To date, in format 2006-01-02")

	return cmd
}

type Cost struct {
	Dimensions []string
	CostType   string
	Amount     *float64
	Unit       string
}

type Costs []Cost

var alwasyPrintDimensions = []string{
	"Amazon Managed Service for Prometheus",
}

func hasInCommon[T constraints.Ordered](s1, s2 []T) bool {
	for _, e1 := range s1 {
		for _, e2 := range s2 {
			if e1 == e2 {
				return true
			}
		}
	}
	return false
}

func (costs Costs) String(groupByDimensions []string, costTypes []string) string {
	cs := costs
	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(append(groupByDimensions, costTypes...))

	formatedCosts := map[string][]Cost{}
	for _, c := range cs {
		dimensionString := strings.Join(c.Dimensions, "#")
		_, ok := formatedCosts[dimensionString]
		if !ok {
			formatedCosts[dimensionString] = []Cost{}
		}
		formatedCosts[dimensionString] = append(formatedCosts[dimensionString], c)
	}
	tableRows := [][]string{}
	for k, v := range formatedCosts {
		output := strings.Split(k, "#")
		allZero := true
		for _, costType := range costTypes {
			for _, c := range v {
				if costType == c.CostType {
					valueStr := "n/a"
					if c.Amount == nil {
						log.Printf("Warning: missing a data point")
					} else {
						valueStr = fmt.Sprintf("%.2f", *c.Amount) + " " + c.Unit
						if (c.Unit == "USD" && *c.Amount > 0.01) || hasInCommon(alwasyPrintDimensions, c.Dimensions) {
							allZero = false
						}
					}
					output = append(output, valueStr)
				}
			}
		}

		if !allZero {
			tableRows = append(tableRows, output)
		}
	}
	sort.Slice(tableRows, func(i, j int) bool {
		if tableRows[i] == nil || tableRows[j] == nil {
			return true
		}
		return tableRows[i][0] > tableRows[j][0]
	})
	tb.AppendBulk(tableRows)
	tb.Render()
	return buf.String()
}

func createCost(dimensions []string, costType string, v costexplorer_types.MetricValue) Cost {
	var amount *float64
	unit := "n/a"
	if v.Amount != nil {
		parsed, err := strconv.ParseFloat(*v.Amount, 64)
		if err != nil {
			fmt.Println(err)
		} else {
			amount = &parsed
		}
	}
	if v.Unit != nil {
		unit = *v.Unit
	}

	return Cost{
		Dimensions: dimensions,
		CostType:   costType,
		Amount:     amount,
		Unit:       unit,
	}
}

func createReport(groupByDimensions []string, accounts []string, services []string, metrics []string) {
	cfg, err := aws.New(&aws.Config{
		DebugAPICalls: false,
		Region:        region,
	})
	if err != nil {
		log.Panicf("failed to create AWS session %v", err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	results, err := billing.GetCostAndUsage(ctx, cfg, fromTime, toTime, groupByDimensions, accounts, services, metrics)
	if err != nil {
		log.Panicf("failed to get aws cost: %v", err)
	}
	costs := make(Costs, 0)
	for _, r := range results {
		fmt.Println("Estimated? ", r.Estimated)
		for _, g := range r.Groups {
			for k, v := range g.Metrics {
				costs = append(costs, createCost(g.Keys, k, v))
			}
		}
	}

	fmt.Println(costs.String(groupByDimensions, metrics))
}

var detailedGroupBy = []string{"SERVICE", "USAGE_TYPE"}
var briefGroupBy = []string{"SERVICE", "LINKED_ACCOUNT"}

const (
	metricsUnblendedCost = "UnblendedCost"
	metricsUsageQuantity = "UsageQuantity"
)

var metricsCostOnly = []string{metricsUnblendedCost}
var metricsCostAndUsage = []string{metricsUnblendedCost, metricsUsageQuantity}

func listFunc(cmd *cobra.Command, args []string) {
	var err error
	fromTime, err = time.Parse("2006-01-02", fromDate)
	if err != nil {
		log.Panic("Wrong date format: ", fromTime, err)
	}
	toTime, err = time.Parse("2006-01-02", toDate)
	if err != nil {
		log.Panic("Wrong date format: ", fromTime, err)
	}

	a := []string{}
	if accounts != "" {
		a = strings.Split(accounts, ",")
	}
	ec2Services := []string{}
	if computeOnly {
		ec2Services = []string{"EC2 - Other", "Amazon Elastic Compute Cloud - Compute"}
	}

	fmt.Println("Detailed usage and cost")
	createReport(detailedGroupBy, a, ec2Services, metricsCostAndUsage)

	fmt.Println("Per service cost")
	createReport(briefGroupBy, a, ec2Services, metricsCostOnly)

	fmt.Println("Accounts regional cost table")
	createReport([]string{"LINKED_ACCOUNT", "REGION"}, a, ec2Services, metricsCostOnly)

	fmt.Println("Account total cost")
	createReport([]string{"LINKED_ACCOUNT"}, a, ec2Services, metricsCostOnly)
}

// Service list:
// Account total cost
// AWS Backup
// AWS CodeArtifact
// AWS Data Transfer
// AWS Directory Service
// AWS Key Management Service
// AWS Secrets Manager
// Amazon DynamoDB
// Amazon EC2 Container Registry (ECR)
// EC2 - Other
// Amazon Elastic Compute Cloud - Compute
// Amazon Elastic Container Service for Kubernetes
// Amazon Elastic File System
// Amazon Elastic Load Balancing
// Amazon Managed Service for Prometheus
// Amazon Relational Database Service
// Amazon Route 53
// Amazon Simple Notification Service
// Amazon Simple Queue Service
// Amazon Simple Storage Service
// Amazon Virtual Private Cloud
