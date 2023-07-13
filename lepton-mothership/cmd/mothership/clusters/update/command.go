// Package update implements update command.
package update

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	clusterName string
	gitRef      string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters update" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "update",
		Short: "update a cluster",
		Run:   updateFunc,
	}
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "Name of the cluster to update")
	cmd.PersistentFlags().StringVarP(&gitRef, "git-ref", "g", "main", "Git ref to use for the cluster")
	return cmd
}

func updateFunc(cmd *cobra.Command, args []string) {
	if clusterName == "" {
		log.Fatal("cluster name is required")
	}

	token := common.ReadTokenFromFlag(cmd)
	mothershipURL := common.ReadMothershipURLFromFlag(cmd)

	// get the existing cluster
	cli := goclient.NewHTTP(mothershipURL, token)
	b, err := cli.RequestPath(http.MethodGet, "/clusters/"+clusterName, nil, nil)
	if err != nil {
		log.Fatal("error sending cluster get request: ", err)
	}
	cluster := crdv1alpha1.LeptonCluster{}
	err = json.Unmarshal(b, &cluster)
	if err != nil {
		log.Fatal("error unmarshalling cluster: ", err)
	}

	// update cluster spec
	clusterspec := cluster.Spec
	clusterspec.GitRef = gitRef

	b, err = json.Marshal(clusterspec)
	if err != nil {
		log.Fatal("failed to marshal cluster spec: ", err)
	}
	log.Printf("updating cluster spec: %s", b)

	b, err = cli.RequestPath(http.MethodPatch, "/clusters", nil, b)
	if err != nil {
		log.Fatal("error sending HTTP Patch request: ", err)
	}

	fmt.Printf("successfully sent %q: %s\n", http.MethodPatch, string(b))
}
