// Package eks implements EKS utils.
package eks

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	"github.com/aws/aws-sdk-go/aws/awserr"
)

// Returns true if the specified cluster does not exist, thus deleted.
func IsClusterDeleted(eksAPI *aws_eks_v2.Client, name string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	eksOut, err := eksAPI.DescribeCluster(ctx, &aws_eks_v2.DescribeClusterInput{
		Name: &name,
	})
	cancel()
	if err == nil {
		version, status, health := GetClusterStatus(eksOut)
		log.Printf("cluster %q still exists with version %q, status %q, health %q", name, version, status, health)
		return false, nil
	}

	if IsErrClusterDeleted(err) {
		log.Printf("cluster %q already deleted", name)
		return true, nil
	}
	return false, err
}

// Returns version, status, and health information.
func GetClusterStatus(out *aws_eks_v2.DescribeClusterOutput) (string, string, string) {
	version := *out.Cluster.Version
	status := string(out.Cluster.Status)

	health := "OK"
	if out.Cluster.Health != nil && out.Cluster.Health.Issues != nil && len(out.Cluster.Health.Issues) > 0 {
		health = fmt.Sprintf("%+v", out.Cluster.Health.Issues)
	}

	return version, status, health
}

func IsErrClusterDeleted(err error) bool {
	if err == nil {
		return false
	}
	awsErr, ok := err.(awserr.Error)
	if ok && awsErr.Code() == "ResourceNotFoundException" &&
		strings.HasPrefix(awsErr.Message(), "No cluster found for") {
		// ResourceNotFoundException: No cluster found for name: aws-k8s-tester-155468BC717E03B003\n\tstatus code: 404, request id: 1e3fe41c-b878-11e8-adca-b503e0ba731d
		return true
	}

	// must check the string
	// sometimes EKS API returns untyped error value
	return strings.Contains(err.Error(), "No cluster found for")
}
