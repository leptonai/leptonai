// Package purge implements purge command.
package purge

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	leptonaws "github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/ebs"
	"github.com/leptonai/lepton/go-pkg/aws/efs"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/go-pkg/aws/iam"
	"github.com/leptonai/lepton/go-pkg/aws/kms"
	"github.com/leptonai/lepton/go-pkg/aws/route53"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/mothership/cmd/mothership/util"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_iam_v2 "github.com/aws/aws-sdk-go-v2/service/iam"
	"github.com/spf13/cobra"
)

var (
	svcCodes []string
	region   string
	provider string

	mothershipURL string
	token         string
	contextPath   string

	enableEBS     bool
	enableEFS     bool
	enableR53     bool
	r53HostZoneID string
	enableKMS     bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "purge",
		Short: "purge cloud resources",
		Run:   purgeFunc,
	}
	cmd.PersistentFlags().StringSliceVar(&svcCodes, "service-codes", []string{"ec2", "eks"}, "Service codes to purge")
	cmd.PersistentFlags().StringVarP(&region, "region", "r", "us-east-1", "AWS region to query")
	cmd.PersistentFlags().StringVarP(&mothershipURL, "mothership-url", "u", "", "Mothership API endpoint URL")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call (overwrites --token-path)")
	cmd.PersistentFlags().StringVarP(&contextPath, "token-path", "p", common.DefaultContextPath, "Directory path that contains the context of the motership API call (to be overwritten by non-empty --token)")

	cmd.PersistentFlags().BoolVarP(&enableKMS, "kms-enabled", "k", false, "Enable purging KMS")
	cmd.PersistentFlags().BoolVarP(&enableEBS, "ebs-enabled", "", false, "Enable EBS volume deletion")
	cmd.PersistentFlags().BoolVarP(&enableEFS, "efs-enabled", "", false, "Enable EFS volume deletion")
	cmd.PersistentFlags().BoolVarP(&enableR53, "r53-enabled", "", false, "Enable Route53 record deletion")
	cmd.PersistentFlags().StringVarP(&r53HostZoneID, "r53-host-zone-id", "", "Z007822916VK7B4DFVMP7", "Route53 host zone ID")

	// TODO: support other providers
	cmd.PersistentFlags().StringVarP(&provider, "provider", "", "aws", "Provider to check the quota")

	return cmd
}

func purgeFunc(cmd *cobra.Command, args []string) {
	ctx := common.ReadContext(cmd)
	token, mothershipURL = ctx.Token, ctx.URL

	cli := goclient.NewHTTP(mothershipURL, token)
	clusters, err := util.ListClusters(cli)
	if err != nil {
		log.Fatalf("failed to list clusters %v", err)
	}
	workspaces, err := util.ListWorkspaces(cli, false)
	if err != nil {
		log.Fatalf("failed to list clusters %v", err)
	}

	cls := map[string]bool{}
	for _, c := range clusters {
		cls[c.Name] = true
	}
	wps := map[string]bool{}
	for _, w := range workspaces {
		wps[w.Name] = true
	}

	purgeAWS(cls, wps)
}

func purgeAWS(cls map[string]bool, wps map[string]bool) {
	cfg, err := leptonaws.New(&leptonaws.Config{
		DebugAPICalls: false,
		Region:        region,
	})
	if err != nil {
		log.Fatalf("failed to create AWS session %v", err)
	}

	if enableKMS {
		if err := purgeKMS(cfg, cls); err != nil {
			log.Fatalf("failed to purge all dangling KMS keys %v", err)
		}
	}

	if enableR53 {
		err = purgeRoute53Records(cfg, r53HostZoneID, wps)
		if err != nil {
			log.Printf("failed to purge all dangling route53 records %v", err)
		}
	}

	if enableEFS {
		err = purgeEFS(cfg, wps)
		if err != nil {
			log.Printf("failed to purge all dangling EFS %v", err)
		}
	}

	if enableEBS {
		err = purgeEBS(cfg)
		if err != nil {
			log.Printf("failed to purge all dangling EBS %v", err)
		}
	}

	purgeS3()

	purgeEKS()

	purgeNAT()

	purgeALB()

	purgeAMP()

	purgeIAM(cfg)
}

func purgeEFS(cfg aws.Config, wps map[string]bool) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	fss, err := efs.ListFileSystems(ctx, cfg, nil)
	if err != nil {
		log.Fatalf("failed to list EFS %v", err)
	}

	deleteIDs := []string{}

	for _, fs := range fss {
		wpn, ok := fs.Tags["LeptonWorkspaceName"]
		if !ok {
			parts := strings.Split(fs.Name, "-")
			wpn = parts[2]
		}

		if _, ok := wps[wpn]; !ok {
			deleteIDs = append(deleteIDs, fs.ID)
			fmt.Printf("deleting dangling EFS %s %s\n", fs.Name, fs.ID)
		} else {
			fmt.Printf("workspace %s is still alive, keeping EFS %s %s\n", wpn, fs.Name, fs.ID)
		}
	}

	return efs.DeleteFileSystem(ctx, cfg, deleteIDs)
}

func purgeS3() {}

func purgeEKS() {
	// find EKS clusters that are not in the clusters list
	// delete all node groups
	// delete the eks cluster
}

func purgeNAT() {}

func purgeALB() {}

func purgeAMP() {}

func purgeIAM(cfg aws.Config) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	eksClusters, err := eks.ListClusters(ctx, cfg.Region, cfg, -1)
	cancel()
	if err != nil {
		log.Fatalf("failed to list EKS clusters %v", err)
	}
	log.Printf("listed %d EKS clusters", len(eksClusters))

	existingOIDCIssuers := make(map[string]struct{})
	for _, c := range eksClusters {
		existingOIDCIssuers[c.OIDCIssuer] = struct{}{}
	}

	iamCli := aws_iam_v2.NewFromConfig(cfg)
	ctx, cancel = context.WithTimeout(context.Background(), 3*time.Minute)
	roles, err := iam.ListRoles(ctx, cfg, -1)
	cancel()
	if err != nil {
		log.Fatalf("failed to list IAM roles %v", err)
	}
	log.Printf("listed %d IAM roles", len(roles))

	for _, role := range roles {
		if len(role.AssumeRolePolicyDocument.Statement) > 0 {
			federated := role.AssumeRolePolicyDocument.Statement[0].Principal.Federated
			if _, exists := existingOIDCIssuers[federated]; exists {
				log.Printf("federated OIDC issuer %q in use -- skipping", federated)
				continue
			}
		}

		log.Printf("deleting the role %q", role.ARN)
		ctx, cancel = context.WithTimeout(context.Background(), 3*time.Minute)
		_, err = iamCli.DeleteRole(ctx, &aws_iam_v2.DeleteRoleInput{RoleName: &role.Name})
		cancel()
		if err != nil {
			log.Printf("failed to delete %q (%v)", role.ARN, err)
		} else {
			log.Printf("deleted %q", role.ARN)
		}
	}

	ctx, cancel = context.WithTimeout(context.Background(), 5*time.Minute)
	policies, err := iam.ListPolicies(ctx, cfg, -1)
	cancel()
	if err != nil {
		log.Fatalf("failed to list IAM policies %v", err)
	}
	for _, policy := range policies {
		if policy.AWSManaged {
			log.Printf("skipping aws managed policy %q", policy.ARN)
			continue
		}

		log.Printf("deleting the policy %q", policy.ARN)
		ctx, cancel = context.WithTimeout(context.Background(), 3*time.Minute)
		_, err = iamCli.DeletePolicy(ctx, &aws_iam_v2.DeletePolicyInput{PolicyArn: &policy.ARN})
		cancel()
		if err != nil {
			log.Printf("failed to delete %q (%v)", policy.ARN, err)
		} else {
			log.Printf("deleted %q", policy.ARN)
		}
	}
}

func purgeEBS(cfg aws.Config) error {
	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	defer cancel()
	vs, err := ebs.ListEBS(ctx, cfg, true)
	if err != nil {
		return err
	}

	return ebs.DeleteVolumes(ctx, cfg, vs)
}

// purgeRoute53Records deletes all Route53 records that are not in the workspace list.
// Since external dns does not support tagging, so we have to do name based matching and filtering.
func purgeRoute53Records(cfg aws.Config, hostedZoneID string, wps map[string]bool) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	rs, err := route53.ListRecords(ctx, cfg, hostedZoneID)
	if err != nil {
		return err
	}

	for _, recordSet := range rs {
		if recordSet.Name == nil {
			fmt.Println("Record name is nil, skipping...")
			continue
		}
		name := *recordSet.Name
		if name == "cloud.lepton.ai." || name == "app.lepton.ai." {
			fmt.Println("skipping the global root record:", name, recordSet.Type)
			continue
		}
		if strings.Contains(name, "mothership") {
			fmt.Println("skipping the mothership record:", name, recordSet.Type)
			continue
		}

		// TODO: handle .app.lepton.ai. records
		prefix := name[:len(name)-len(".cloud.lepton.ai.")]
		prefix = strings.TrimPrefix(prefix, "cname-")
		workspaceName := strings.Split(prefix, "-")[0]

		_, ok := wps[workspaceName]
		if ok {
			fmt.Println("Workspace", workspaceName, "is still alive, skipping the route53 record:", name, recordSet.Type)
			continue
		}

		fmt.Println("Workspace", workspaceName, "is already deleted, deleting the route53 record:", name, recordSet.Type)
		err = route53.DeleteRecord(ctx, cfg, hostedZoneID, recordSet)
		if err != nil {
			fmt.Println("Failed to delete record:", err)
		} else {
			fmt.Println("Record deleted successfully.")
		}
	}

	return nil
}

func purgeKMS(cfg aws.Config, cls map[string]bool) error {
	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	defer cancel()

	as, err := kms.ListAliases(ctx, cfg)
	if err != nil {
		return err
	}

	for _, alias := range as {
		names := strings.Split(*alias.AliasName, "/")
		if len(names) >= 3 {
			if names[1] != "eks" { // skip non eks kms keys
				continue
			}
			name := names[len(names)-1]
			if cls[name] {
				fmt.Printf("cluster %s is still alive, skipping the kms key: %s", name, *alias.AliasName)
				continue
			}
		}

		fmt.Printf("deleting kms key %s\n", *alias.AliasName)

		err = kms.ScheduleDeleteKeyByID(ctx, cfg, alias.TargetKeyId)
		if err != nil {
			log.Printf("failed to delete kms key %s: %v", *alias.AliasName, err)
		}
	}

	return err
}
