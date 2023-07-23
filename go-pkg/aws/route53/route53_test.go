package route53

import (
	"context"
	"fmt"
	"os"
	"testing"

	"github.com/leptonai/lepton/go-pkg/aws"
)

func TestRoute53(t *testing.T) {
	if os.Getenv("RUN_AWS_TESTS") != "1" {
		t.Skip()
	}

	cfg, err := aws.New(&aws.Config{
		Region: "us-east-1",
	})
	if err != nil {
		t.Fatal(err)
	}

	cloudZone := "Z007822916VK7B4DFVMP7"
	records, err := ListRecords(context.Background(), cfg, cloudZone)
	if err != nil {
		t.Fatal(err)
	}

	for _, record := range records {
		fmt.Println(record.Name, record.Type)
	}
}
