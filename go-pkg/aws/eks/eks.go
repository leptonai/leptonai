// Package eks implements EKS utils.
package eks

import (
	"bytes"
	"context"
	"encoding/base64"
	"errors"
	"fmt"
	"log"
	"os/exec"
	"sort"
	"strings"
	"time"

	leptonaws "github.com/leptonai/lepton/go-pkg/aws"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	aws_elbv2_v2 "github.com/aws/aws-sdk-go-v2/service/elasticloadbalancingv2"
	"github.com/aws/aws-sdk-go/aws/awserr"
	"github.com/olekukonko/tablewriter"
	clientcmd_api_v1 "k8s.io/client-go/tools/clientcmd/api/v1"
)

func ListClusters(ctx context.Context, region string, cfg aws.Config, limit int) ([]Cluster, error) {
	cli := aws_eks_v2.NewFromConfig(cfg)
	return listClusters(ctx, region, cli, "", limit)
}

func GetCluster(ctx context.Context, region string, cli *aws_eks_v2.Client, clusterName string) (Cluster, error) {
	cs, err := listClusters(ctx, region, cli, clusterName, 1)
	if err != nil {
		return Cluster{}, err
	}
	if len(cs) != 1 {
		return Cluster{}, errors.New("not found")
	}
	return cs[0], nil
}

func listClusters(ctx context.Context, region string, cli *aws_eks_v2.Client, clusterName string, limit int) ([]Cluster, error) {
	clusters := make([]Cluster, 0)

	var nextToken *string = nil
done:
	for i := 0; i < 20; i++ {
		clusterNames := []string{clusterName}
		if clusterName == "" {
			out, err := cli.ListClusters(ctx, &aws_eks_v2.ListClustersInput{
				NextToken: nextToken,
			})
			if err != nil {
				return nil, err
			}
			clusterNames = out.Clusters
			nextToken = out.NextToken
		}

		log.Printf("inspecting %d clusters", len(clusterNames))
		for _, cname := range clusterNames {
			cl, err := inspectCluster(ctx, region, "UNKNOWN", cli, nil, cname)
			if err != nil {
				return nil, err
			}

			clusters = append(clusters, cl)
			if limit >= 0 && len(clusters) >= limit {
				log.Printf("already listed %d clusters with limit %d -- skipping the rest", len(clusters), limit)
				break done
			}
		}

		log.Printf("listed %d clusters so far with limit %d", len(clusters), limit)
		if nextToken == nil {
			// no more resources are available
			break
		}

		// TODO: add wait to prevent api throttle (rate limit)?
	}

	sort.SliceStable(clusters, func(i, j int) bool {
		return clusters[i].ARN < clusters[j].ARN
	})
	return clusters, nil
}

// Inspects EKS resources based on the cluster name.
// It may take long time, if the account has many number of ELB resources
// since ELB does not support filter-based list APIs.
func InspectClusters(ctx context.Context, clusters map[string]crdv1alpha1.LeptonCluster) ([]Cluster, error) {
	log.Printf("inspect %d clusters", len(clusters))

	// for each region, in case one mothership handles all regions
	eksAPIs := make(map[string]*aws_eks_v2.Client)
	elbv2APIs := make(map[string]*aws_elbv2_v2.Client)
	for _, cs := range clusters {
		if _, ok := eksAPIs[cs.Spec.Region]; ok {
			continue
		}
		cfg, err := leptonaws.New(&leptonaws.Config{
			// TODO: make these configurable, or derive from cluster spec
			DebugAPICalls: false,
			Region:        cs.Spec.Region,
		})
		if err != nil {
			return nil, err
		}
		eksAPIs[cs.Spec.Region] = aws_eks_v2.NewFromConfig(cfg)
		elbv2APIs[cs.Spec.Region] = aws_elbv2_v2.NewFromConfig(cfg)
	}

	// region -> vpc id -> elb v2 arns
	regionToVPCToELBv2s := make(map[string]map[string][]string)
	for reg, elbv2API := range elbv2APIs {
		if _, ok := regionToVPCToELBv2s[reg]; !ok {
			regionToVPCToELBv2s[reg] = make(map[string][]string)
		}
		vpcToELBv2s := regionToVPCToELBv2s[reg]

		log.Printf("fetching all ELB v2 for the region %q", reg)
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

			// TODO: add wait to prevent api throttle (rate limit)?
		}
	}

	css := make([]Cluster, 0)
	for clusterName, cs := range clusters {
		c, err := inspectCluster(
			ctx,
			cs.Spec.Region,
			string(cs.Status.State),
			eksAPIs[cs.Spec.Region],
			regionToVPCToELBv2s[cs.Spec.Region],
			clusterName,
		)
		if err != nil {
			return nil, err
		}
		css = append(css, c)
	}

	sort.SliceStable(css, func(i, j int) bool {
		if css[i].CreatedAt == css[j].CreatedAt {
			return css[i].Name < css[j].Name
		}

		// descending order by create timestamp
		// that way, deleted clusters with zero timestamp
		// value are located at last
		return !css[i].CreatedAt.Before(css[j].CreatedAt)
	})
	return css, nil
}

func inspectCluster(
	ctx context.Context,
	region string,
	mothershipState string,
	eksAPI *aws_eks_v2.Client,
	vpcToELBv2s map[string][]string,
	clusterName string,
) (Cluster, error) {
	eksOut, err := eksAPI.DescribeCluster(
		ctx,
		&aws_eks_v2.DescribeClusterInput{
			Name: &clusterName,
		},
	)
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
	vpcID := ""
	if eksOut.Cluster.ResourcesVpcConfig != nil {
		vpcID = *eksOut.Cluster.ResourcesVpcConfig.VpcId
	}

	oidcIssuer := ""
	if eksOut.Cluster.Identity != nil && eksOut.Cluster.Identity.Oidc != nil {
		oidcIssuer = *eksOut.Cluster.Identity.Oidc.Issuer
	}

	endpoint := ""
	if eksOut.Cluster.Endpoint != nil {
		endpoint = *eksOut.Cluster.Endpoint
	}

	ca := ""
	if eksOut.Cluster.CertificateAuthority != nil {
		ca = *eksOut.Cluster.CertificateAuthority.Data
	}

	version, status, health := GetClusterStatus(eksOut)
	attachedELBs := make([]string, 0)
	if vpcToELBv2s != nil {
		attachedELBs = vpcToELBv2s[vpcID]
	}
	c := Cluster{
		Name:   clusterName,
		ARN:    *eksOut.Cluster.Arn,
		Region: region,

		Version:         version,
		PlatformVersion: platformVeresion,
		MothershipState: mothershipState,
		Status:          status,
		Health:          health,

		CreatedAt: *eksOut.Cluster.CreatedAt,

		VPCID:             vpcID,
		AttachedELBv2ARNs: attachedELBs,

		Endpoint:             endpoint,
		CertificateAuthority: ca,
		OIDCIssuer:           oidcIssuer,

		// to populate below
		NodeGroups: nil,
	}

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

		k8sVersion := "UNKNOWN"
		if out.Nodegroup.Version != nil {
			k8sVersion = *out.Nodegroup.Version
		}
		releaseVersion := "UNKNOWN"
		if out.Nodegroup.ReleaseVersion != nil {
			releaseVersion = *out.Nodegroup.ReleaseVersion
		}

		nodes[i] = MNG{
			Name: mngName,
			ARN:  *out.Nodegroup.NodegroupArn,

			K8SVersion:     k8sVersion,
			ReleaseVersion: releaseVersion,

			CapacityType: string(out.Nodegroup.CapacityType),
			Status:       string(out.Nodegroup.Status),

			AttachedASGs: asgs,
		}
	}
	c.NodeGroups = nodes

	return c, nil
}

type Cluster struct {
	Name   string `json:"name"`
	ARN    string `json:"arn"`
	Region string `json:"region"`

	Version         string `json:"version"`
	PlatformVersion string `json:"platform-version"`
	MothershipState string `json:"mothership-state"`
	Status          string `json:"status"`
	Health          string `json:"health"`

	CreatedAt time.Time `json:"created-at"`

	VPCID             string   `json:"vpc-id"`
	AttachedELBv2ARNs []string `json:"attached-elbv2-arns"`

	Endpoint             string `json:"endpoint"`
	CertificateAuthority string `json:"-"`
	OIDCIssuer           string `json:"oidc-issuer"`

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
	tb.Append([]string{"MOTHERSHIP STATE", c.MothershipState})
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

func (c Cluster) Kubeconfig() (clientcmd_api_v1.Config, error) {
	awsPath, err := exec.LookPath("aws")
	if err != nil {
		return clientcmd_api_v1.Config{}, fmt.Errorf("aws cli not found %w", err)
	}

	decoded, err := base64.StdEncoding.DecodeString(c.CertificateAuthority)
	if err != nil {
		return clientcmd_api_v1.Config{}, fmt.Errorf("failed to decode certificate authority %w", err)
	}

	kcfg := clientcmd_api_v1.Config{
		Clusters: []clientcmd_api_v1.NamedCluster{
			{
				Name: c.ARN,
				Cluster: clientcmd_api_v1.Cluster{
					Server:                   c.Endpoint,
					CertificateAuthorityData: decoded,
				},
			},
		},
		Contexts: []clientcmd_api_v1.NamedContext{
			{
				Name: c.ARN,
				Context: clientcmd_api_v1.Context{
					Cluster:  c.ARN,
					AuthInfo: c.ARN,
				},
			},
		},
		CurrentContext: c.ARN,
		AuthInfos: []clientcmd_api_v1.NamedAuthInfo{
			{
				Name: c.ARN,
				AuthInfo: clientcmd_api_v1.AuthInfo{
					Exec: &clientcmd_api_v1.ExecConfig{
						APIVersion: "client.authentication.k8s.io/v1beta1",
						Command:    awsPath,
						Args: []string{
							"--region",
							c.Region,
							"eks",
							"get-token",
							"--cluster-name",
							c.Name,
							"--output",
							"json",
						},
					},
				},
			},
		},
	}
	return kcfg, nil
}

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
