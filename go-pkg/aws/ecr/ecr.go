// Package ecr implements ECR utils.
package ecr

import (
	"context"
	"encoding/json"
	"log"
	"sort"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_ecr_v2 "github.com/aws/aws-sdk-go-v2/service/ecr"
	"github.com/aws/aws-sdk-go-v2/service/ecr/types"
	"github.com/aws/aws-sdk-go/service/ecr"
	"github.com/aws/smithy-go"
)

type Repository struct {
	AccountID       string
	Name            string
	ARN             string
	URI             string
	LifecyclePolicy LifecyclePolicy
	Images          []Image
}

func parsePolicyText(b string) (LifecyclePolicy, error) {
	p := LifecyclePolicy{}
	err := json.Unmarshal([]byte(b), &p)
	return p, err
}

type LifecyclePolicy struct {
	Rules           []LifecyclePolicyRule `json:"rules"`
	LastEvaluatedAt time.Time
}

type LifecyclePolicyRule struct {
	RulePriority int    `json:"rulePriority,omitempty"`
	Description  string `json:"description,omitempty"`
	Selection    struct {
		TagStatus   string `json:"tagStatus,omitempty"`
		CountType   string `json:"countType,omitempty"`
		CountUnit   string `json:"countUnit,omitempty"`
		CountNumber int    `json:"countNumber,omitempty"`
	} `json:"selection,omitempty"`
	Action struct {
		Type string `json:"type,omitempty"`
	} `json:"action,omitempty"`
}

type Image struct {
	Tags        []string
	Digest      string
	PushedTime  time.Time
	SizeInBytes int64
}

const describeInterval = 5 * time.Second

// Lists ECR repositories up to 5,000.
func ListRepositories(ctx context.Context, cfg aws.Config, repoLimit int, imgLimit int) ([]Repository, error) {
	cli := aws_ecr_v2.NewFromConfig(cfg)

	repositories := make([]Repository, 0)

	var nextToken *string = nil
	for i := 0; i < 50; i++ {
		// max return is 100 items
		out, err := cli.DescribeRepositories(ctx, &aws_ecr_v2.DescribeRepositoriesInput{
			NextToken: nextToken,
		})
		if err != nil {
			return nil, err
		}

		for _, repo := range out.Repositories {
			policy, err := cli.GetLifecyclePolicy(ctx, &aws_ecr_v2.GetLifecyclePolicyInput{
				RepositoryName: repo.RepositoryName,
				RegistryId:     repo.RegistryId,
			})

			lifecyclePolicy := LifecyclePolicy{}
			if err != nil {
				// returns "github.com/aws/aws-sdk-go/aws/awserr.Error" for SDK v1
				// returns "github.com/aws/smithy-go.OperationError" for SDK v2
				awsErr, ok := err.(*smithy.OperationError)
				if !ok {
					return nil, err
				}
				if !strings.Contains(awsErr.Error(), ecr.ErrCodeLifecyclePolicyNotFoundException) {
					return nil, err
				}
				log.Printf("repository %q has no lifecycle policy (error code %v)", *repo.RepositoryName, awsErr.Err)
			} else {
				lifecyclePolicy, err = parsePolicyText(*policy.LifecyclePolicyText)
				if err != nil {
					return nil, err
				}
				lifecyclePolicy.LastEvaluatedAt = *policy.LastEvaluatedAt
			}

			imgs, err := listImages(ctx, cli, *repo.RepositoryName, *repo.RegistryId, imgLimit)
			if err != nil {
				return nil, err
			}

			r := Repository{
				AccountID:       *repo.RegistryId,
				Name:            *repo.RepositoryName,
				ARN:             *repo.RepositoryArn,
				URI:             *repo.RepositoryUri,
				LifecyclePolicy: lifecyclePolicy,
				Images:          imgs,
			}

			repositories = append(repositories, r)
			if repoLimit >= 0 && len(repositories) >= repoLimit {
				log.Printf("for %q, already listed %d repositories with limit %d -- skipping the rest", *repo.RepositoryName, len(repositories), repoLimit)
				break
			}

			time.Sleep(describeInterval)
		}

		log.Printf("listed %d repositories so far with limit %d", len(repositories), repoLimit)
		nextToken = out.NextToken
		if nextToken == nil {
			// no more resources are available
			break
		}

		time.Sleep(describeInterval)
	}

	return repositories, nil
}

func listImages(ctx context.Context, cli *aws_ecr_v2.Client, repoName string, registryID string, imgLimit int) ([]Image, error) {
	images := make([]Image, 0)

	var nextToken *string = nil
	for i := 0; i < 50; i++ {
		// max return is 100 items
		out, err := cli.ListImages(ctx, &aws_ecr_v2.ListImagesInput{
			RepositoryName: &repoName,
			RegistryId:     &registryID,
			NextToken:      nextToken,
		})
		if err != nil {
			return nil, err
		}

		if out.ImageIds == nil || len(out.ImageIds) == 0 {
			break
		}

		imgs, err := describeImages(ctx, cli, repoName, registryID, out.ImageIds)
		if err != nil {
			return nil, err
		}
		images = append(images, imgs...)

		if imgLimit >= 0 && len(images) >= imgLimit {
			log.Printf("for %q, already listed %d images with limit %d -- skipping the rest", repoName, len(images), imgLimit)
			break
		}

		nextToken = out.NextToken
		if nextToken == nil {
			// no more resources are available
			break
		}

		time.Sleep(describeInterval)
	}

	// descending order, latest at first
	sort.SliceStable(images, func(i, j int) bool {
		if images[i].PushedTime == images[j].PushedTime {
			return images[i].Digest < images[j].Digest
		}
		return images[i].PushedTime.UnixNano() > images[j].PushedTime.UnixNano()
	})

	return images, nil
}

func describeImages(ctx context.Context, cli *aws_ecr_v2.Client, repoName string, registryID string, imgIDs []types.ImageIdentifier) ([]Image, error) {
	images := make([]Image, 0)

	var nextToken *string = nil
	for i := 0; i < 50; i++ {
		// max return is 100 items
		out, err := cli.DescribeImages(ctx, &aws_ecr_v2.DescribeImagesInput{
			RepositoryName: &repoName,
			RegistryId:     &registryID,
			ImageIds:       imgIDs,
			NextToken:      nextToken,
		})
		if err != nil {
			return nil, err
		}

		for _, v := range out.ImageDetails {
			img := Image{
				Tags:        v.ImageTags,
				Digest:      *v.ImageDigest,
				PushedTime:  *v.ImagePushedAt,
				SizeInBytes: *v.ImageSizeInBytes,
			}

			images = append(images, img)
		}

		nextToken = out.NextToken
		if nextToken == nil {
			// no more resources are available
			break
		}

		time.Sleep(describeInterval)
	}

	return images, nil
}
