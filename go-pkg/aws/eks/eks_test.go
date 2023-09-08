package eks

import (
	"context"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"sigs.k8s.io/yaml"
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

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	clusters, err := ListClusters(ctx, "us-east-1", cfg, 10)
	cancel()
	if err != nil {
		t.Fatal(err)
	}

	for _, cl := range clusters {
		t.Logf("%s %s %s\n%+v\n\n", cl.CertificateAuthority, cl.Endpoint, cl.OIDCIssuer, cl)

		kcfg, err := cl.Kubeconfig()
		if err != nil {
			t.Fatal(err)
		}

		kb, err := yaml.Marshal(kcfg)
		if err != nil {
			t.Fatal(err)
		}

		fmt.Println(string(kb))
	}
}
