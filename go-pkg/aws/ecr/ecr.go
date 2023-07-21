// Package ecr implements ECR utils.
package ecr

import (
	"context"
	"log"
	"sort"
	"time"

	aws_ecr_v2 "github.com/aws/aws-sdk-go-v2/service/ecr"
	"github.com/aws/aws-sdk-go-v2/service/ecr/types"
)

type Repository struct {
	AccountID string
	Name      string
	ARN       string
	URI       string
	Images    []Image
}

type Image struct {
	Tags        []string
	Digest      string
	PushedTime  time.Time
	SizeInBytes int64
}

const describeInterval = 5 * time.Second

// Lists ECR repositories up to 5,000.
func ListRepositories(ctx context.Context, cli *aws_ecr_v2.Client, repoLimit int, imgLimit int) ([]Repository, error) {
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
			imgs, err := listImages(ctx, cli, *repo.RepositoryName, *repo.RegistryId, imgLimit)
			if err != nil {
				return nil, err
			}

			r := Repository{
				AccountID: *repo.RegistryId,
				Name:      *repo.RepositoryName,
				ARN:       *repo.RepositoryArn,
				URI:       *repo.RepositoryUri,
				Images:    imgs,
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
