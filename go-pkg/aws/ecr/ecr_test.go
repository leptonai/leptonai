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

func Test_parsePolicyText(t *testing.T) {
	txt := `{"rules":[{"rulePriority":1,"description":"keep latest forever","selection":{"tagStatus":"tagged","tagPrefixList":["latest"],"countType":"sinceImagePushed","countUnit":"days","countNumber":3650},"action":{"type":"expire"}},{"rulePriority":2,"description":"delete test in 1 day","selection":{"tagStatus":"tagged","tagPrefixList":["test"],"countType":"sinceImagePushed","countUnit":"days","countNumber":1},"action":{"type":"expire"}},{"rulePriority":3,"description":"delete untagged in 1 day","selection":{"tagStatus":"untagged","countType":"sinceImagePushed","countUnit":"days","countNumber":1},"action":{"type":"expire"}},{"rulePriority":4,"description":"delete others (release images) in 1 year","selection":{"tagStatus":"any","countType":"sinceImagePushed","countUnit":"days","countNumber":365},"action":{"type":"expire"}}]}`
	p, err := parsePolicyText(txt)
	if err != nil {
		t.Fatal(err)
	}
	t.Logf("%+v", p)

	if len(p.Rules) != 4 {
		t.Fatalf("len(p.Rules) = %d; want 4", len(p.Rules))
	}
}
