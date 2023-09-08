package iam

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
)

func TestListRoles(t *testing.T) {
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
	roles, err := ListRoles(ctx, cfg, 10)
	cancel()
	if err != nil {
		t.Fatal(err)
	}

	for _, role := range roles {
		t.Logf("%+v", role)
		if len(role.AssumeRolePolicyDocument.Statement) > 0 {
			// e.g.,
			// &{Federated: Service:resource-explorer-2.amazonaws.com}
			// &{Federated:arn:aws:iam::605454121064:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/5DF09B6AF786C15C1DF142838C32D467 Service:}
			t.Logf("principal: %+v", role.AssumeRolePolicyDocument.Statement[0].Principal)
		}
	}
}
