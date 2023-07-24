// Package delete implements delete command.
package delete

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/go-pkg/prompt"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	clusterName string
	strategy    string
	dry         bool
	force       bool
	autoApprove bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters delete" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "delete",
		Short: "Delete the given cluster",
		Run:   deleteFunc,
	}
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "Name of the cluster to delete")
	cmd.PersistentFlags().BoolVarP(&force, "force", "f", false, "Force delete the cluster with its workspaces. Only valid when strategy=mothership")
	cmd.PersistentFlags().StringVar(&strategy, "strategy", "mothership", "'mothership' to schedule a delete, 'provider' to call provider API directly")
	cmd.PersistentFlags().BoolVar(&dry, "dry", true, "Set to false to disable dry mode (only used for 'provider' based deletion)")
	cmd.PersistentFlags().BoolVar(&autoApprove, "auto-approve", false, "Set to auto-approve the action without prompt (if you know what you're doing)")
	return cmd
}

func deleteFunc(cmd *cobra.Command, args []string) {
	if clusterName == "" {
		log.Fatal("cluster name is required")
	}

	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL

	if !autoApprove {
		if !prompt.IsInputYes(fmt.Sprintf("Confirm to delete cluster %q via %q\n", clusterName, mothershipURL)) {
			return
		}
	}

	cli := goclient.NewHTTP(mothershipURL, token)

	switch strategy {
	case "mothership":
		log.Printf("mothership-based delete on %q", clusterName)
		path := "/clusters/" + clusterName
		if force {
			path += "?force=true"
		}
		b, err := cli.RequestPath(http.MethodDelete, path, nil, nil)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Printf("successfully sent %q: %s\n", http.MethodDelete, string(b))

	case "provider":
		log.Printf("provider-based delete on %q", clusterName)

		b, err := cli.RequestPath(http.MethodGet, "/clusters/"+clusterName, nil, nil)
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
		css := make(map[string]crdv1alpha1.LeptonCluster)
		css[clusterName] = cluster

		ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
		cs, err := eks.InspectClusters(ctx, css)
		cancel()
		if err != nil {
			log.Fatalf("failed to inspect clusters (%v)", err)
		}
		if len(cs) != 1 {
			log.Fatalf("unexpected %d cluster(s) found, expecting %q", len(cs), clusterName)
		}
		c := cs[0]
		fmt.Printf("deleting the following resources:\n\n%s\n", c.String())

		if dry {
			log.Print("skipping delete (dry mode)")
			return
		}

		// TODO: implement resource cleanups based on inspect results
		// TODO: this is unsafe... implement access control
		// TODO: implement prompt

	default:
		log.Fatalf("unknown strategy %q", strategy)
	}
}
