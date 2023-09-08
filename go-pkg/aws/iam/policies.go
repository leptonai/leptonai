package iam

import (
	"context"
	"log"
	"sort"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_iam_v2 "github.com/aws/aws-sdk-go-v2/service/iam"
)

type Policy struct {
	Name             string
	ARN              string
	AttachedEntities int
	Tags             map[string]string

	// Set true if prefixed by "arn:aws:iam::aws:policy/...".
	// e.g., "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
	// e.g., "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
	// e.g., "arn:aws:iam::605454121064:policy/alb-policy-dev" is set to false.
	AWSManaged bool
}

// List policies up to 5,000.
func ListPolicies(ctx context.Context, cfg aws.Config, limit int) ([]Policy, error) {
	policies := make([]Policy, 0)
	cli := aws_iam_v2.NewFromConfig(cfg)

	var nextMarker *string = nil
	for i := 0; i < 50; i++ {
		// max return is 100 items
		out, err := cli.ListPolicies(ctx, &aws_iam_v2.ListPoliciesInput{
			Marker: nextMarker,
		})
		if err != nil {
			return nil, err
		}

		for _, o := range out.Policies {
			tags := make(map[string]string)
			for _, v := range o.Tags {
				tags[*v.Key] = *v.Value
			}
			policies = append(policies, Policy{
				Name:             *o.PolicyName,
				ARN:              *o.Arn,
				Tags:             tags,
				AttachedEntities: int(*o.AttachmentCount),
				AWSManaged:       strings.HasPrefix(*o.Arn, "arn:aws:iam::aws:policy/"),
			})
		}

		if limit >= 0 && len(policies) >= limit {
			log.Printf("already listed %d policies with limit %d -- skipping the rest", len(policies), limit)
			break
		}

		log.Printf("listed %d policies so far with limit %d", len(policies), limit)
		nextMarker = out.Marker
		if nextMarker == nil {
			// no more resources are available
			break
		}

		// TODO: add wait to prevent api throttle (rate limit)?
	}

	sort.SliceStable(policies, func(i, j int) bool {
		return policies[i].ARN < policies[j].ARN
	})
	return policies, nil
}
