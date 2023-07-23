// Package secrets implements AWS secret manager utils.
package secrets

import (
	"context"

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
