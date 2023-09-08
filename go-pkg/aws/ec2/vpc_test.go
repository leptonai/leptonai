package ec2

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
)

func TestListVPCs(t *testing.T) {
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
	vpcs, err := ListVPCs(ctx, cfg)
	cancel()
	if err != nil {
		t.Fatal(err)
	}

	for i, v := range vpcs {
		t.Logf("VPC ID: %q (%s)\n", *v.VpcId, v.State)

		if i > 0 {
			continue
		}

		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		vpc, err := GetVPC(ctx, cfg, *v.VpcId)
		cancel()
		if err != nil {
			t.Fatal(err)
		}
		t.Logf("VPC: %+v\n", vpc)

		ctx, cancel = context.WithTimeout(context.Background(), 10*time.Second)
		subnets, err := GetVPCSubnets(ctx, cfg, *v.VpcId)
		cancel()
		if err != nil {
			t.Fatal(err)
		}
		for _, s := range subnets {
			t.Logf("subnet %s in availability zone: %s", *s.SubnetId, *s.AvailabilityZone)
		}
	}
}
