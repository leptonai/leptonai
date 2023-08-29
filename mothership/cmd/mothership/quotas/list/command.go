// Package list implements list command.
package list

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	svcquota "github.com/leptonai/lepton/go-pkg/aws/svc-quota"

	"github.com/aws/aws-sdk-go-v2/service/cloudwatch"
	aws_svcquotas_v2 "github.com/aws/aws-sdk-go-v2/service/servicequotas"
	"github.com/spf13/cobra"
)

var (
	svcCodes []string
	region   string
	provider string
	all      bool
)

// https://github.com/leptonai/lepton/blob/main/docs/internal/infra/AWS.md/#L26-L42
var quotaCodeList = map[string][]string{
	"eks": {
		"L-1194D53C", // EKS
	},
	"vpc": {
		"L-F678F1CE", // VPC
		"L-FE5A380F", // NAT GATEWAY
	},
	"elasticloadbalancing": {
		"L-53DA6B97", // ALB"
	},
	"ec2": {
		"L-0263D0A3", // EIP
		"L-1216C47A", // Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances
		"L-DB2E81BA", // Running On-Demand G and VT instances
		"L-CAE24619", // g4dn.xlarge
		"L-A6E7FE5E", // g5.2xlarge
		"L-86A789C3", // p4de.24xlarge
	},
	"s3": {
		"L-DC2B2D3D", // s3 buckets
	},
	"elasticfilesystem": {
		"L-848C634D", // The maximum number of file systems that a customer account can have in an AWS Region
		"L-7391004C", // The maximum number of EFS mount targets allowed for each VPC
	},
}

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all quotas",
		Run:   listFunc,
	}
	cmd.PersistentFlags().StringSliceVar(&svcCodes, "service-codes", []string{"ec2", "eks"}, "Service codes to list the quotas")
	cmd.PersistentFlags().StringVarP(&region, "region", "r", "us-east-1", "AWS region to query")
	cmd.PersistentFlags().BoolVarP(&all, "all", "a", false, "Print a full list of aws quotas")

	// TODO: support other providers
	cmd.PersistentFlags().StringVarP(&provider, "provider", "p", "aws", "Provider to check the quota")

	return cmd
}

func listFunc(cmd *cobra.Command, args []string) {
	cfg, err := aws.New(&aws.Config{
		DebugAPICalls: false,
		Region:        region,
	})
	if err != nil {
		log.Panicf("failed to create AWS session %v", err)
	}
	cli := aws_svcquotas_v2.NewFromConfig(cfg)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)

	cwClient := cloudwatch.NewFromConfig(cfg)
	if !all {
		quotas, err := svcquota.ListImportantQuotas(ctx, cli, cwClient, quotaCodeList)
		cancel()
		if err != nil {
			log.Fatalf("failed to list service quotas, %v", err)
		}
		fmt.Println(quotas.String())
	} else {
		quotas, err := svcquota.ListServiceQuotas(ctx, cli, cwClient, svcCodes...)
		cancel()
		if err != nil {
			log.Fatalf("failed to list service quotas %v", err)
		}
		fmt.Println(quotas.String())
	}
}
