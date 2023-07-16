// Package get implements get command.
package get

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/aws"
	efs "github.com/leptonai/lepton/go-pkg/aws/efs"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	aws_efs_v2 "github.com/aws/aws-sdk-go-v2/service/efs"
	"github.com/spf13/cobra"
)

var (
	workspaceName  string
	inspectVolumes bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get a workspace Spec and Status",
		Run:   getFunc,
	}
	cmd.PersistentFlags().StringVarP(&workspaceName, "workspace-name", "w", "", "Name of the workspace to get")
	cmd.PersistentFlags().BoolVarP(&inspectVolumes, "inspect-volumes", "v", false, "true to show all the mounted volumes")
	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
	if workspaceName == "" {
		log.Fatal("cluster name is required")
	}

	token := common.ReadTokenFromFlag(cmd)
	mothershipURL := common.ReadMothershipURLFromFlag(cmd)

	cli := goclient.NewHTTP(mothershipURL, token)
	b, err := cli.RequestPath(http.MethodGet, "/workspaces/"+workspaceName, nil, nil)
	if err != nil {
		log.Fatal("error sending request: ", err)
	}
	workspace := &crdv1alpha1.LeptonWorkspace{}
	if err := json.Unmarshal(b, &workspace); err != nil {
		log.Fatal("error unmarshalling response: ", err)
	}
	ret, err := json.MarshalIndent(workspace, "", "  ")
	if err != nil {
		log.Fatal("error marshalling response: ", err)
	}
	fmt.Println(string(ret))

	if inspectVolumes {
		inspectEFSFs(cli, workspace)
	}
}

func inspectEFSFs(cli *goclient.HTTP, workspace *crdv1alpha1.LeptonWorkspace) {
	b, err := cli.RequestPath(http.MethodGet, "/clusters/"+workspace.Spec.ClusterName, nil, nil)
	if err != nil {
		log.Fatal("error sending request: ", err)
	}
	cluster := &crdv1alpha1.LeptonCluster{}
	if err := json.Unmarshal(b, &cluster); err != nil {
		log.Fatal("error unmarshalling response: ", err)
	}
	switch cluster.Spec.Provider {
	case "aws":
		if cluster.Spec.Region == "" {
			log.Fatal("unknown region")
		}
		cfg, err := aws.New(&aws.Config{
			DebugAPICalls: false,
			Region:        cluster.Spec.Region,
		})
		if err != nil {
			log.Panicf("failed to create AWS session %v", err)
		}
		cli := aws_efs_v2.NewFromConfig(cfg)

		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
		fss, err := efs.ListFileSystems(ctx, cli)
		cancel()
		if err != nil {
			log.Fatalf("failed to list EFS file systems %v", err)
		}
		found := make([]efs.FileSystem, 0)
		for _, fs := range fss {
			cname := fs.Tags["LeptonClusterName"]
			if cname != workspace.Spec.ClusterName {
				continue
			}

			wname := fs.Tags["LeptonWorkspaceName"]
			if wname != workspaceName {
				continue
			}

			found = append(found, fs)
		}
		if len(found) == 0 {
			log.Printf("no volume mounted for the namespace %q", workspaceName)
			return
		}

		fmt.Println()
		for i, fs := range found {
			fmt.Printf("###\nFile sytem #%02d\n\n", i+1)
			fmt.Println(fs.String())
		}

	default:
		log.Fatalf("unknown provider %q", cluster.Spec.Provider)
	}
}
