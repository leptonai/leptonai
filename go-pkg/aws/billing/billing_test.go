package billing

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
)

func TestBilling(t *testing.T) {
	if os.Getenv("RUN_AWS_TESTS") != "1" {
		t.Skip()
	}

	cfg, err := aws.New(&aws.Config{
		Region: "us-east-1",
	})
	if err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	usage, err := GetCostAndUsage(ctx, cfg, time.Now().Add(-48*time.Hour), time.Now().Add(-24*time.Hour))
	cancel()
	if err != nil {
		t.Fatal(err)
	}

	for _, u := range usage {
		for _, g := range u.Groups {
			t.Logf("%v %v: %v %s", g.Keys[0], g.Keys[1], *g.Metrics["BlendedCost"].Amount, *g.Metrics["BlendedCost"].Unit)
		}
	}
}
