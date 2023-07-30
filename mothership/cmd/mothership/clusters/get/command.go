// Package get implements get command.
package get

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	clusterName string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get a cluster Spec and Status",
		Run:   getFunc,
	}
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "Name of the cluster to get")
	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
	if clusterName == "" {
		log.Fatal("cluster name is required")
	}

	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL

	cli := goclient.NewHTTP(mothershipURL, token)
	b, err := cli.RequestPath(http.MethodGet, "/clusters/"+clusterName, nil, nil)
	if err != nil {
		log.Fatal("error sending request: ", err)
	}
	cluster := &crdv1alpha1.LeptonCluster{}
	if err := json.Unmarshal(b, &cluster); err != nil {
		log.Fatal("error unmarshalling response: ", err)
	}
	ret, err := json.MarshalIndent(cluster, "", "  ")
	if err != nil {
		log.Fatal("error marshalling response: ", err)
	}
	fmt.Println(string(ret))
}
