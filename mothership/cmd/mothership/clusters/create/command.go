// Package create implements create command.
package create

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
	region      string
	gitRef      string
	description string
	dpEnv       string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters create" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "create",
		Short: "Create a cluster",
		Run:   createFunc,
	}
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "Name of the cluster to create")
	cmd.PersistentFlags().StringVarP(&region, "region", "r", "us-east-1", "Set region for cluster spec")
	cmd.PersistentFlags().StringVarP(&gitRef, "git-ref", "g", "main", "Git ref to use for the cluster")
	cmd.PersistentFlags().StringVarP(&description, "description", "d", "From cli for testing", "Description of the cluster")
	cmd.PersistentFlags().StringVarP(&dpEnv, "deployment-environment", "e", "", "Deployment environment (leave empty to set default on the server-side)")
	return cmd
}

func createFunc(cmd *cobra.Command, args []string) {
	if clusterName == "" {
		log.Fatal("cluster name is required")
	}

	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL

	cluster := crdv1alpha1.LeptonClusterSpec{
		DeploymentEnvironment: dpEnv,
		Region:                region,
		Name:                  clusterName,
		GitRef:                gitRef,
		Description:           description,
	}

	b, err := json.Marshal(cluster)
	if err != nil {
		log.Fatal("failed to marshal cluster spec: ", err)
	}

	cli := goclient.NewHTTP(mothershipURL, token)
	b, err = cli.RequestPath(http.MethodPost, "/clusters", nil, b)
	if err != nil {
		log.Fatal("error sending request: ", err)
	}
	fmt.Printf("successfully sent %q: %s\n", http.MethodPost, string(b))
}