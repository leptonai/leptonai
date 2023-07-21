package eks

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"

	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
)

func TestListClusters(t *testing.T) {
	if os.Getenv("RUN_AWS_TESTS") != "1" {
		t.Skip()
	}

	cfg, err := aws.New(&aws.Config{
		Region: "us-east-1",
	})
	if err != nil {
		t.Fatal(err)
	}
	cli := aws_eks_v2.NewFromConfig(cfg)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	clusters, err := ListClusters(ctx, "us-east-1", cli, 10)
	cancel()
	if err != nil {
		t.Fatal(err)
	}

	for _, cl := range clusters {
		t.Logf("%s %s %s\n%+v\n\n", cl.CertificateAuthority, cl.Endpoint, cl.OIDCIssuer, cl)
	}
}
