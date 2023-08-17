// Package secrets implements AWS secret manager utils.
package secrets

import (
	"context"
	"sort"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_secretsmanager_v2 "github.com/aws/aws-sdk-go-v2/service/secretsmanager"
)

// Reads a secret in plaintext from the secret manager.
func Read(ctx context.Context, cfg aws.Config, name string) (string, error) {
	cli := aws_secretsmanager_v2.NewFromConfig(cfg)
	out, err := cli.GetSecretValue(ctx,
		&aws_secretsmanager_v2.GetSecretValueInput{
			SecretId: &name,
		},
	)
	if err != nil {
		return "", err
	}
	return *out.SecretString, nil
}

// Lists secret names from the secret manager.
func List(ctx context.Context, cfg aws.Config) ([]string, error) {
	cli := aws_secretsmanager_v2.NewFromConfig(cfg)

	ss := make([]string, 0)
	var nextToken *string = nil
	for i := 0; i < 20; i++ {
		out, err := cli.ListSecrets(ctx,
			&aws_secretsmanager_v2.ListSecretsInput{
				NextToken: nextToken,
			},
		)
		if err != nil {
			return nil, err
		}

		for _, s := range out.SecretList {
			ss = append(ss, *s.Name)
		}

		if nextToken == nil {
			// no more resources are available
			break
		}
	}

	sort.Strings(ss)
	return ss, nil
}
