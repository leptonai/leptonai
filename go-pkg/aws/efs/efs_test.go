package efs

import (
	"context"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
)

func TestEFS(t *testing.T) {
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
	defer cancel()
	fss, err := ListFileSystems(ctx, cfg, nil)
	if err != nil {
		t.Fatal(err)
	}

	for _, fs := range fss {
		fmt.Println(fs.String())
	}
}
