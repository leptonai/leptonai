// Package eks implements EKS utils.
package eks

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"sort"
	"strings"
	"time"

	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	aws_elbv2_v2 "github.com/aws/aws-sdk-go-v2/service/elasticloadbalancingv2"
	"github.com/aws/aws-sdk-go/aws/awserr"
	"github.com/olekukonko/tablewriter"
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

const describeELBInterval = 5 * time.Second

// Inspects EKS resources based on the cluster name.
// It may take long time, if the account has many number of ELB resources
// since ELB does not support filter-based list APIs.
func InspectClusters(
	ctx context.Context,
	eksAPI *aws_eks_v2.Client,
	elbv2API *aws_elbv2_v2.Client,
	clusterNames ...string) ([]Cluster, error) {
	vpcToELBv2s := make(map[string][]string)
	var nextMarker *string = nil
	for i := 0; i < 10; i++ {
		out, err := elbv2API.DescribeLoadBalancers(ctx, &aws_elbv2_v2.DescribeLoadBalancersInput{
			Marker: nextMarker,
		})
		if err != nil {
			return nil, err
		}

		for _, lb := range out.LoadBalancers {
			vpcID := *lb.VpcId
			arn := *lb.LoadBalancerArn

			elbs, ok := vpcToELBv2s[vpcID]
			if !ok {
				elbs = []string{arn}
			} else {
				elbs = append(elbs, arn)
				sort.Strings(elbs)
			}
			vpcToELBv2s[vpcID] = elbs
		}

		nextMarker = out.NextMarker
		if nextMarker == nil {
			// no more resources are available
			break
		}

		time.Sleep(describeELBInterval)
	}

	cs := make([]Cluster, 0)
	for _, name := range clusterNames {
		c, err := inspectCluster(ctx, eksAPI, vpcToELBv2s, name)
		if err != nil {
			return nil, err
		}
		cs = append(cs, c)
	}

	sort.SliceStable(cs, func(i, j int) bool {
		if cs[i].CreatedAt == cs[j].CreatedAt {
			return cs[i].Name < cs[j].Name
		}
		// descending order by create timestamp
		// that way, deleted clusters with zero timestamp
		// value are located at last
		return !cs[i].CreatedAt.Before(cs[j].CreatedAt)
	})
	return cs, nil
}

func inspectCluster(
	ctx context.Context,
	eksAPI *aws_eks_v2.Client,
	vpcToELBv2s map[string][]string,
	clusterName string,
) (Cluster, error) {
	eksOut, err := eksAPI.DescribeCluster(ctx, &aws_eks_v2.DescribeClusterInput{
		Name: &clusterName,
	})
	if err != nil {
		if IsErrClusterDeleted(err) {
			log.Printf("cluster %q already deleted", clusterName)
			return Cluster{Name: clusterName, Status: "DELETED"}, nil
		}
		return Cluster{}, err
	}

	platformVeresion := "UNKNOWN"
	if eksOut.Cluster.PlatformVersion != nil {
		platformVeresion = *eksOut.Cluster.PlatformVersion
	}
	version, status, health := GetClusterStatus(eksOut)
	c := Cluster{
		Name: clusterName,
		ARN:  *eksOut.Cluster.Arn,

		Version:         version,
		PlatformVersion: platformVeresion,
		Status:          status,
		Health:          health,

		CreatedAt: *eksOut.Cluster.CreatedAt,

		VPCID: *eksOut.Cluster.ResourcesVpcConfig.VpcId,
	}
	c.AttachedELBv2ARNs = vpcToELBv2s[c.VPCID]

	mngs, err := eksAPI.ListNodegroups(ctx, &aws_eks_v2.ListNodegroupsInput{ClusterName: &clusterName})
	if err != nil {
		return c, err
	}
	nodes := make([]MNG, len(mngs.Nodegroups))
	for i := range nodes {
		mngName := mngs.Nodegroups[i]
		out, err := eksAPI.DescribeNodegroup(
			ctx,
			&aws_eks_v2.DescribeNodegroupInput{
				ClusterName:   &clusterName,
				NodegroupName: &mngName,
			})
		if err != nil {
			return c, err
		}

		asgs := make([]string, len(out.Nodegroup.Resources.AutoScalingGroups))
		for i, r := range out.Nodegroup.Resources.AutoScalingGroups {
			asgs[i] = *r.Name
		}

		nodes[i] = MNG{
			Name: mngName,
			ARN:  *out.Nodegroup.NodegroupArn,

			K8SVersion:     *out.Nodegroup.Version,
			ReleaseVersion: *out.Nodegroup.ReleaseVersion,

			CapacityType: string(out.Nodegroup.CapacityType),
			Status:       string(out.Nodegroup.Status),

			AttachedASGs: asgs,
		}
	}
	c.NodeGroups = nodes

	return c, nil
}

type Cluster struct {
	Name string `json:"name"`
	ARN  string `json:"arn"`

	Version         string `json:"version"`
	PlatformVersion string `json:"platform-version"`
	Status          string `json:"status"`
	Health          string `json:"health"`

	CreatedAt time.Time `json:"created-at"`

	VPCID             string   `json:"vpc-id"`
	AttachedELBv2ARNs []string `json:"attached-elbv2-arns"`

	NodeGroups []MNG `json:"node-groups"`
}

type MNG struct {
	Name string `json:"name"`
	ARN  string `json:"arn"`

	K8SVersion     string `json:"k8s-version"`
	ReleaseVersion string `json:"release-version"`

	CapacityType string `json:"capacity-type"`
	Status       string `json:"status"`

	AttachedASGs []string `json:"attached-asgs"`
}

func (c Cluster) String() string {
	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetRowLine(true)
	tb.Append([]string{"CLUSTER KIND", "EKS"})
	tb.Append([]string{"NAME", c.Name})
	tb.Append([]string{"ARN", c.ARN})
	tb.Append([]string{"VERSION", c.Version})
	tb.Append([]string{"PLATFORM VERSION", c.PlatformVersion})
	tb.Append([]string{"STATUS", c.Status})
	tb.Append([]string{"HEALTH", c.Health})
	tb.Append([]string{"CREATED AT", c.CreatedAt.String()})
	tb.Append([]string{"VPC ID", c.VPCID})
	for i, arn := range c.AttachedELBv2ARNs {
		tb.Append([]string{fmt.Sprintf("ATTACHED ELBv2 ARN #%d", i+1), arn})
	}
	tb.Render()

	rs := buf.String()

	if len(c.NodeGroups) == 0 {
		return rs
	}

	for i, mng := range c.NodeGroups {
		buf.Reset()
		tb := tablewriter.NewWriter(buf)
		tb.SetAutoWrapText(false)
		tb.SetAlignment(tablewriter.ALIGN_LEFT)
		tb.SetCenterSeparator("*")
		tb.SetRowLine(true)
		tb.Append([]string{fmt.Sprintf("NODE GROUP #%d", i+1), mng.Name})
		tb.Append([]string{"ARN", mng.ARN})
		tb.Append([]string{"K8S VERSION", mng.K8SVersion})
		tb.Append([]string{"RELEASE VERSION", mng.ReleaseVersion})
		tb.Append([]string{"CAPACITY TYPE", mng.CapacityType})
		tb.Append([]string{"STATUS", mng.Status})
		for j, asg := range mng.AttachedASGs {
			tb.Append([]string{fmt.Sprintf("ATTACHED ASG #%d", j+1), asg})
		}
		tb.Render()

		rs += "\n"
		rs += buf.String()
	}

	return rs
}
