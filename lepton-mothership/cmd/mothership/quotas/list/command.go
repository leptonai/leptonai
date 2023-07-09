// Package list implements list command.
package list

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	svcquota "github.com/leptonai/lepton/go-pkg/aws/svc-quota"

	aws_svcquotas_v2 "github.com/aws/aws-sdk-go-v2/service/servicequotas"
	"github.com/spf13/cobra"
)

var (
	svcCodes []string
	region   string
	provider string
)

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
	quotas, err := svcquota.ListServiceQuotas(ctx, cli, svcCodes...)
	cancel()
	if err != nil {
		log.Fatalf("failed to list service quotas %v", err)
	}
	fmt.Println(quotas.String())
}
