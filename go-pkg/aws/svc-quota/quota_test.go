package svcquota

import (
	"context"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"

	aws_svcquotas_v2 "github.com/aws/aws-sdk-go-v2/service/servicequotas"
)

// As of today, there are >200 services.
func TestListServices(t *testing.T) {
	if os.Getenv("RUN_AWS_TESTS") != "1" {
		t.Skip()
	}

	if _, err := aws.New(nil); err == nil {
		t.Fatal("expected error, got nil")
	}
	cfg, err := aws.New(&aws.Config{
		Region: "us-east-1",
	})
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Credentials == nil {
		t.Skip("cannot create session; nil Credentials")
	}

	cli := aws_svcquotas_v2.NewFromConfig(cfg)

	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	svcs, err := ListServices(ctx, cli)
	cancel()
	if err != nil {
		t.Fatal(err)
	}
	for _, s := range svcs {
		t.Logf("service code %q, name %q", *s.ServiceCode, *s.ServiceName)
	}
}

func TestListServiceQuotas(t *testing.T) {
	if os.Getenv("RUN_AWS_TESTS") != "1" {
		t.Skip()
	}

	if _, err := aws.New(nil); err == nil {
		t.Fatal("expected error, got nil")
	}
	cfg, err := aws.New(&aws.Config{
		Region: "us-east-1",
	})
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Credentials == nil {
		t.Skip("cannot create session; nil Credentials")
	}

	cli := aws_svcquotas_v2.NewFromConfig(cfg)

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	quotas, err := ListServiceQuotas(ctx, cli, "ec2", "eks")
	cancel()
	if err != nil {
		t.Fatal(err)
	}
	fmt.Println(quotas.String())
}
