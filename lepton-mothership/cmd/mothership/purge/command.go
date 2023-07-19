// Package purge implements purge command.
package purge

import (
	"context"
	"fmt"
	"log"
	"strings"

	goclient "github.com/leptonai/lepton/go-client"
	leptonaws "github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/util"
	"github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/route53"
	"github.com/aws/aws-sdk-go-v2/service/route53/types"
	"github.com/spf13/cobra"
)

var (
	svcCodes []string
	region   string
	provider string

	mothershipURL string
	token         string
	tokenPath     string
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
	for _, c := range clusters {
		for _, w := range c.Status.Workspaces {
			wps[w] = true
		}
	}

	purgeAWS(wps)
}

func purgeAWS(wps map[string]bool) {
	cfg, err := leptonaws.New(&leptonaws.Config{
		DebugAPICalls: false,
		Region:        region,
	})
	if err != nil {
		log.Fatalf("failed to create AWS session %v", err)
	}

	hostZoneID := "Z007822916VK7B4DFVMP7"
	err = purgeRoute53Records(cfg, hostZoneID, wps)
	if err != nil {
		log.Printf("failed to purge route53 records %v", err)
	}

	purgeEFS()

	purgeS3()

	purgeEKS()

	purgeNAT()

	purgeALB()

	purgeAMP()

	purgeIAM()
}

func purgeEFS() {}

func purgeS3() {}

func purgeEKS() {}

func purgeNAT() {}

func purgeALB() {}

func purgeAMP() {}

func purgeIAM() {}

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
			if strings.Contains(name, "motership") {
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
