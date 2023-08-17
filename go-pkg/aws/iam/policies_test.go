package iam

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
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

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	policies, err := ListPolicies(ctx, cfg, 10)
	cancel()
	if err != nil {
		t.Fatal(err)
	}

	for _, policy := range policies {
		t.Logf("%+v", policy)
	}
}
