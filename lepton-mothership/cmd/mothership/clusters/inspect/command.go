// Package inspect implements inspect command.
package inspectEKS

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	aws_elbv2_v2 "github.com/aws/aws-sdk-go-v2/service/elasticloadbalancingv2"
	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
)

var (
	clusterName string
	outputType  string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "inspect-eks",
		Short: "Inspects EKS cluster(s)",
		Run:   inspectFunc,
	}
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "n", "", "Cluster name to inspect (leave empty to inspect all)")
	cmd.PersistentFlags().StringVarP(&outputType, "output", "o", "table", "Output type (either table or json)")
	return cmd
}

func inspectFunc(cmd *cobra.Command, args []string) {
	clusterNames := make([]string, 0)

	if clusterName != "" {
		clusterNames = append(clusterNames, clusterName)
	} else {
		token := common.ReadTokenFromFlag(cmd)
		mothershipURL := common.ReadMothershipURLFromFlag(cmd)

		req, err := http.NewRequestWithContext(
			context.Background(),
			"GET",
			mothershipURL,
			nil,
		)
		if err != nil {
			log.Fatalf("failed to create base query request %v", err)
		}
		req.Header.Add("Authorization", "Bearer "+token)
		log.Printf("sending GET to: %s", req.URL.String())

		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			log.Fatalf("failed http request %v", err)
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			log.Fatalf("failed http request %v", resp.Status)
		}

		var rs []*crdv1alpha1.LeptonCluster
		if err = json.NewDecoder(resp.Body).Decode(&rs); err != nil {
			log.Fatalf("failed to decode %v", err)
		}
		log.Printf("fetched %d clusters", len(rs))

		for _, r := range rs {
			clusterNames = append(clusterNames, r.Name)
		}
	}

	cfg, err := aws.New(&aws.Config{
		// TODO: make these configurable, or derive from cluster spec
		DebugAPICalls: false,
		Region:        "us-east-1",
	})
	if err != nil {
		log.Fatalf("failed to create AWS session %v", err)
	}
	eksAPI := aws_eks_v2.NewFromConfig(cfg)
	elbv2API := aws_elbv2_v2.NewFromConfig(cfg)

	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	cs, err := eks.InspectClusters(ctx, eksAPI, elbv2API, clusterNames...)
	cancel()
	if err != nil {
		log.Fatalf("failed to inspect clusters (%v)", err)
	}

	for _, c := range cs {
		fmt.Printf("\n\n-----\n\n")
		switch outputType {
		case "table":
			fmt.Println(c.String())
		case "json":
			b, err := json.Marshal(c)
			if err != nil {
				log.Fatalf("failed to marshal json %v", err)
			}
			fmt.Println(string(b))
		default:
			log.Fatalf("unknown output type %q", outputType)
		}
	}
}
