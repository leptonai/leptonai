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
	"github.com/leptonai/lepton/go-pkg/aws/efs"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/go-pkg/aws/iam"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/util"
	"github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/aws/aws-sdk-go-v2/aws"
	aws_efs_v2 "github.com/aws/aws-sdk-go-v2/service/efs"
	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	aws_iam_v2 "github.com/aws/aws-sdk-go-v2/service/iam"
	"github.com/aws/aws-sdk-go-v2/service/kms"
	"github.com/aws/aws-sdk-go-v2/service/route53"
	"github.com/aws/aws-sdk-go-v2/service/route53/types"
	"github.com/spf13/cobra"
)

var (
	svcCodes []string
	region   string
	provider string

	mothershipURL  string
	token          string
	tokenPath      string
	enablePurgeKMS bool
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
	cmd.PersistentFlags().StringVarP(&mothershipURL, "mothership-url", "u", "https://mothership.cloud.lepton.ai/api/v1", "Mothership API endpoint URL")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call (overwrites --token-path)")
	cmd.PersistentFlags().StringVarP(&tokenPath, "token-path", "p", common.DefaultTokenPath, "File path that contains the beaer token for API call (to be overwritten by non-empty --token)")
	cmd.PersistentFlags().BoolVarP(&enablePurgeKMS, "enalbe-purge-kms", "k", false, "Enable purging KMS and not others")

	// TODO: support other providers
	cmd.PersistentFlags().StringVarP(&provider, "provider", "", "aws", "Provider to check the quota")

	return cmd
}

func purgeFunc(cmd *cobra.Command, args []string) {
	token = common.ReadTokenFromFlag(cmd)
	mothershipURL = common.ReadMothershipURLFromFlag(cmd)

	cli := goclient.NewHTTP(mothershipURL, token)
	clusters, err := util.ListClusters(cli)
	if err != nil {
		log.Fatalf("failed to list clusters %v", err)
	}

	cmap := map[string]*v1alpha1.LeptonCluster{}
	for _, c := range clusters {
		cmap[c.Name] = c
	}

	wps := map[string]bool{}
	cls := map[string]bool{}
	for _, c := range clusters {
		cls[c.Name] = true
		for _, w := range c.Status.Workspaces {
			wps[w] = true
		}
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

	if enablePurgeKMS {
		if err := purgeKMS(cfg, cls); err != nil {
			log.Fatalf("failed to purge KMS %v", err)
		}
		return
	}

	hostZoneID := "Z007822916VK7B4DFVMP7"
	err = purgeRoute53Records(cfg, hostZoneID, wps)
	if err != nil {
		log.Printf("failed to purge all dangling route53 records %v", err)
	}

	err = purgeEFS(cfg, wps)
	if err != nil {
		log.Printf("failed to purge all dangling EFS %v", err)
	}

	purgeS3()

	purgeEKS()

	purgeNAT()

	purgeALB()

	purgeAMP()

	purgeIAM(cfg)
}

func purgeEFS(cfg aws.Config, wps map[string]bool) error {
	cli := aws_efs_v2.NewFromConfig(cfg)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	fss, err := efs.ListFileSystems(ctx, cli)
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

	return efs.DeleteFileSystem(ctx, cli, deleteIDs)
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
	eksCli := aws_eks_v2.NewFromConfig(cfg)

	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	eksClusters, err := eks.ListClusters(ctx, cfg.Region, eksCli, -1)
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
	roles, err := iam.ListRoles(ctx, iamCli, -1)
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
	policies, err := iam.ListPolicies(ctx, iamCli, -1)
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

// purgeRoute53Records deletes all Route53 records that are not in the workspace list.
// Since external dns does not support tagging, so we have to do name based matching and filtering.
func purgeRoute53Records(cfg aws.Config, hostedZoneID string, wps map[string]bool) error {
	client := route53.NewFromConfig(cfg)

	var nextr *string
	for {
		input := &route53.ListResourceRecordSetsInput{
			HostedZoneId:    aws.String(hostedZoneID),
			StartRecordName: nextr,
		}
		result, err := client.ListResourceRecordSets(context.TODO(), input)
		if err != nil {
			return err
		}

		for _, recordSet := range result.ResourceRecordSets {
			if recordSet.Name == nil {
				fmt.Println("Record name is nil, skipping...")
				continue
			}
			name := *recordSet.Name
			if name == "cloud.lepton.ai." {
				fmt.Println("skipping the global root record:", name, recordSet.Type)
				continue
			}
			if strings.Contains(name, "mothership") {
				fmt.Println("skipping the mothership record:", name, recordSet.Type)
				continue
			}

			prefix := name[:len(name)-len(".cloud.lepton.ai.")]
			prefix = strings.TrimPrefix(prefix, "cname-")
			workspaceName := strings.Split(prefix, "-")[0]

			_, ok := wps[workspaceName]
			if !ok {
				fmt.Println("Workspace", workspaceName, "is already deleted, deleting the route53 record:", name, recordSet.Type)

				change := types.Change{
					Action:            types.ChangeActionDelete,
					ResourceRecordSet: &recordSet,
				}
				batchChangeInput := &route53.ChangeResourceRecordSetsInput{
					HostedZoneId: aws.String(hostedZoneID),
					ChangeBatch: &types.ChangeBatch{
						Changes: []types.Change{change},
					},
				}

				// Execute the batch change to delete the records
				_, err = client.ChangeResourceRecordSets(context.TODO(), batchChangeInput)
				if err != nil {
					fmt.Println("Failed to delete record:", err)
				} else {
					fmt.Println("Record deleted successfully.")
				}
			} else {
				fmt.Println("Workspace", workspaceName, "is still alive, skipping the route53 record:", name, recordSet.Type)
			}
		}

		if result.NextRecordName == nil {
			break
		}
		nextr = result.NextRecordName
	}

	return nil
}

func purgeKMS(cfg aws.Config, cls map[string]bool) error {
	var purgePendingWindowInDays int32 = 7
	client := kms.NewFromConfig(cfg)
	marker := ""
	for {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
		defer cancel()
		input := &kms.ListAliasesInput{}
		if marker != "" {
			input.Marker = &marker
		}
		aliases, err := client.ListAliases(ctx, input)
		if err != nil {
			return err
		}
		for _, alias := range aliases.Aliases {
			names := strings.Split(*alias.AliasName, "/")
			if len(names) >= 3 {
				if names[1] != "eks" { // skip non eks kms keys
					continue
				}
				name := names[len(names)-1]
				if cls[name] {
					log.Printf("cluster %s is still alive, skipping the kms key: %s", name, *alias.AliasName)
					continue
				}
			}
			log.Printf("deleting kms key %s\n", *alias.AliasName)
			_, err := client.ScheduleKeyDeletion(ctx, &kms.ScheduleKeyDeletionInput{
				KeyId:               alias.TargetKeyId,
				PendingWindowInDays: &purgePendingWindowInDays,
			})
			if err != nil {
				log.Printf("failed to delete kms key %s: %v", *alias.AliasName, err)
			}
		}
		if !aliases.Truncated {
			break
		}
		marker = *aliases.NextMarker
	}
	return nil
}
