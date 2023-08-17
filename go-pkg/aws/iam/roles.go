package iam

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"sort"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_iam_v2 "github.com/aws/aws-sdk-go-v2/service/iam"
)

type Role struct {
	Name string
	ARN  string

	// Can be either of the formats.
	AssumeRolePolicyDocument       AssumeRolePolicyDocument
	AssumeRolePolicyDocumentSingle AssumeRolePolicyDocumentSingle

	Tags map[string]string
}

// List roles up to 5,000.
func ListRoles(ctx context.Context, cfg aws.Config, limit int) ([]Role, error) {
	roles := make([]Role, 0)
	cli := aws_iam_v2.NewFromConfig(cfg)

	var nextMarker *string = nil
	for i := 0; i < 50; i++ {
		// max return is 100 items
		out, err := cli.ListRoles(ctx, &aws_iam_v2.ListRolesInput{
			Marker: nextMarker,
		})
		if err != nil {
			return nil, err
		}

		for _, o := range out.Roles {
			tags := make(map[string]string)
			for _, v := range o.Tags {
				tags[*v.Key] = *v.Value
			}

			role := Role{
				Name: *o.RoleName,
				ARN:  *o.Arn,
				Tags: tags,
			}

			txt, err := url.QueryUnescape(*o.AssumeRolePolicyDocument)
			if err != nil {
				return nil, fmt.Errorf("failed to escape AssumeRolePolicyDocument:\n%s\n\n(%v)", *o.AssumeRolePolicyDocument, err)
			}

			doc, docSingle := new(AssumeRolePolicyDocument), new(AssumeRolePolicyDocumentSingle)
			if err = json.Unmarshal([]byte(txt), doc); err != nil {
				doc = nil
				log.Printf("retrying unmarshal %v", err)
				if err = json.Unmarshal([]byte(txt), docSingle); err != nil {
					return nil, fmt.Errorf("failed to unmarshal AssumeRolePolicyDocument/Single:\n%s\n\n(%v)", txt, err)
				}
			}
			role.AssumeRolePolicyDocument = *doc
			role.AssumeRolePolicyDocumentSingle = *docSingle

			roles = append(roles, role)
		}

		if limit >= 0 && len(roles) >= limit {
			log.Printf("already listed %d roles with limit %d -- skipping the rest", len(roles), limit)
			break
		}

		log.Printf("listed %d roles so far with limit %d", len(roles), limit)
		nextMarker = out.Marker
		if nextMarker == nil {
			// no more resources are available
			break
		}

		// TODO: add wait to prevent api throttle (rate limit)?
	}

	sort.SliceStable(roles, func(i, j int) bool {
		return roles[i].ARN < roles[j].ARN
	})
	return roles, nil
}

// PolicyDocument is the IAM policy document.
type PolicyDocument struct {
	Version   string
	Statement []StatementEntry
}

// StatementEntry is the entry in IAM policy document "Statement" field.
type StatementEntry struct {
	Effect    string          `json:"Effect,omitempty"`
	Action    []string        `json:"Action,omitempty"`
	Resource  string          `json:"Resource,omitempty"`
	Principal *PrincipalEntry `json:"Principal,omitempty"`
}

type AssumeRolePolicyDocument struct {
	Version   string                               `json:"Version"`
	Statement []*AssumeRolePolicyDocumentStatement `json:"Statement"`
}

type AssumeRolePolicyDocumentSingle struct {
	Version   string                                     `json:"Version"`
	Statement []*AssumeRolePolicyDocumentStatementSingle `json:"Statement"`
}

type AssumeRolePolicyDocumentStatement struct {
	Sid       string          `json:"Sid"`
	Effect    string          `json:"Effect"`
	Principal *PrincipalEntry `json:"Principal,omitempty"`
}

// PrincipalEntry represents the policy document Principal.
type PrincipalEntry struct {
	Federated string `json:"Federated,omitempty"`
	Service   string `json:"Service,omitempty"`
}

type AssumeRolePolicyDocumentStatementSingle struct {
	Effect    string          `json:"Effect"`
	Principal *PrincipalEntry `json:"Principal,omitempty"`
}
