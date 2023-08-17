package ec2

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
)

func TestListENIs(t *testing.T) {
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
	enis, err := ListENIs(ctx, cfg)
	cancel()
	if err != nil {
		t.Fatal(err)
	}

	for i, v := range enis {
		t.Logf("ENI: %q (%s, %s)\n", *v.NetworkInterfaceId, *v.PrivateDnsName, v.Status)

		if i > 0 {
			continue
		}

		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		eni, err := GetENI(ctx, cfg, *v.NetworkInterfaceId)
		cancel()
		if err != nil {
			t.Fatal(err)
		}
		t.Logf("ENI: %+v\n", eni)
	}
}
