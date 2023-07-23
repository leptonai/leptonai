package ebs

import (
	"context"
	"fmt"
	"os"
	"testing"

	"github.com/leptonai/lepton/go-pkg/aws"
)

func TestEBS(t *testing.T) {
	if os.Getenv("RUN_AWS_TESTS") != "1" {
		t.Skip()
	}

	cfg, err := aws.New(&aws.Config{
		Region: "us-east-1",
	})
	if err != nil {
		t.Fatal(err)
	}

	ebss, err := ListEBS(context.Background(), cfg, false)
	if err != nil {
		t.Fatal(err)
	}

	for _, ebs := range ebss {
		fmt.Println(ebs.VolumeId)
	}
}
