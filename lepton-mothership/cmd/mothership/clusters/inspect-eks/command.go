// Package inspect_eks implements inspect-eks command.
package inspect_eks

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
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
	token := common.ReadTokenFromFlag(cmd)
	mothershipURL := common.ReadMothershipURLFromFlag(cmd)
	cli := goclient.NewHTTP(mothershipURL, token)

	// cluster name -> cluster object
	css := make(map[string]crdv1alpha1.LeptonCluster)

	if clusterName != "" {
		log.Printf("fetching a single cluster %q via mothership API", clusterName)
		b, err := cli.RequestURL(http.MethodGet, mothershipURL+"/"+clusterName, nil, nil)
		if err != nil {
			log.Fatal(err)
		}
		var cluster crdv1alpha1.LeptonCluster
		if err = json.Unmarshal(b, &cluster); err != nil {
			log.Fatalf("failed to decode %v", err)
		}
		if cluster.Spec.Region == "" {
			log.Printf("cluster %q spec may be outdated -- region is not populated, default to us-east-1", clusterName)
			cluster.Spec.Region = "us-east-1"
		}
		css[clusterName] = cluster
	} else {
		log.Printf("fetching all clusters via mothership API")
		b, err := cli.RequestURL(http.MethodGet, mothershipURL, nil, nil)
		if err != nil {
			log.Fatal(err)
		}
		var clusters []*crdv1alpha1.LeptonCluster
		if err = json.Unmarshal(b, &clusters); err != nil {
			log.Fatalf("failed to decode %v", err)
		}
		for _, cluster := range clusters {
			if cluster.Spec.Region == "" {
				log.Printf("cluster %q spec may be outdated -- region is not populated, default to us-east-1", cluster.Name)
				cluster.Spec.Region = "us-east-1"
			}
			css[cluster.Name] = *cluster
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	cs, err := eks.InspectClusters(ctx, css)
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
