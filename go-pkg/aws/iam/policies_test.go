package iam

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"

	aws_iam_v2 "github.com/aws/aws-sdk-go-v2/service/iam"
)

func TestListPolicies(t *testing.T) {
	if os.Getenv("RUN_AWS_TESTS") != "1" {
		t.Skip()
	}

	cfg, err := aws.New(&aws.Config{
		Region: "us-east-1",
	})
	if err != nil {
		t.Fatal(err)
	}
	cli := aws_iam_v2.NewFromConfig(cfg)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	policies, err := ListPolicies(ctx, cli, 10)
	cancel()
	if err != nil {
		t.Fatal(err)
	}

	for _, policy := range policies {
		t.Logf("%+v", policy)
	}
}
