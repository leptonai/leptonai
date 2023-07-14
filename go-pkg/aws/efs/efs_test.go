package efs

import (
	"context"
	"fmt"
	"os"
	"testing"

	"github.com/leptonai/lepton/go-pkg/aws"

	aws_efs_v2 "github.com/aws/aws-sdk-go-v2/service/efs"
)

func TestCreds(t *testing.T) {
	if os.Getenv("RUN_AWS_TESTS") != "1" {
		t.Skip()
	}

	cfg, err := aws.New(&aws.Config{
		Region: "us-east-1",
	})
	if err != nil {
		t.Fatal(err)
	}
	cli := aws_efs_v2.NewFromConfig(cfg)

	fss, err := ListFileSystems(context.Background(), cli)
	if err != nil {
		t.Fatal(err)
	}

	for _, fs := range fss {
		fmt.Println(fs.String())
	}
}
