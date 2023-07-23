package ecr

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
)

func TestListRepositories(t *testing.T) {
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
	repos, err := ListRepositories(ctx, cfg, 10, 10)
	cancel()
	if err != nil {
		t.Fatal(err)
	}

	for _, repo := range repos {
		t.Logf("%+v", repo)
	}
}
