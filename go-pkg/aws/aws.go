package aws

import (
	"context"
	"errors"
	"fmt"
	"time"

	aws_v2 "github.com/aws/aws-sdk-go-v2/aws"
	config_v2 "github.com/aws/aws-sdk-go-v2/config"
	aws_sts_v2 "github.com/aws/aws-sdk-go-v2/service/sts"
)

// Config defines a top-level AWS API configuration to create a session.
type Config struct {
	// TODO: set custom logger?

	// DebugAPICalls is true to log all AWS API call debugging messages.
	DebugAPICalls bool

	// Region is a separate AWS geographic area for EKS service.
	// Each AWS Region has multiple, isolated locations known as Availability Zones.
	Region string
}

// New creates a new AWS session.
// Specify a custom endpoint for tests.
func New(cfg *Config) (awsCfg aws_v2.Config, err error) {
	if cfg == nil {
		return aws_v2.Config{}, errors.New("got empty config")
	}
	if cfg.Region == "" {
		return aws_v2.Config{}, fmt.Errorf("missing region")
	}

	optFns := []func(*config_v2.LoadOptions) error{
		(func(*config_v2.LoadOptions) error)(config_v2.WithRegion(cfg.Region)),
	}
	if cfg.DebugAPICalls {
		lvl := aws_v2.LogSigning |
			aws_v2.LogRetries |
			aws_v2.LogRequest |
			aws_v2.LogRequestWithBody |
			aws_v2.LogResponse |
			aws_v2.LogResponseWithBody
		optFns = append(optFns, (func(*config_v2.LoadOptions) error)(config_v2.WithClientLogMode(lvl)))
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	awsCfg, err = config_v2.LoadDefaultConfig(ctx, optFns...)
	cancel()
	if err != nil {
		return aws_v2.Config{}, fmt.Errorf("failed to load config %v", err)
	}

	return awsCfg, nil
}

func GetCallerIdentity() (*aws_sts_v2.GetCallerIdentityOutput, error) {
	cfg, err := New(&Config{Region: "us-east-1"})
	if err != nil {
		return nil, err
	}
	cli := aws_sts_v2.NewFromConfig(cfg)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return cli.GetCallerIdentity(ctx, &aws_sts_v2.GetCallerIdentityInput{})
}
