// Package list implements list command.
package list

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/util"
	"github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
	"github.com/manifoldco/promptui"

	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
)

var (
	output           string
	selectKubeconfig bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all the clusters (either EKS/*), use 'inspect' to get individual clusters",
		Run:   listFunc,
	}
	cmd.PersistentFlags().StringVarP(&output, "output", "o", "table", "Output format, either 'rawjson' or 'table'")
	cmd.PersistentFlags().BoolVarP(&selectKubeconfig, "select-kubeconfig", "k", false, "Set true to interactive select a cluster to write kubeconfig")
	return cmd
}

func listFunc(cmd *cobra.Command, args []string) {
	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL
	if output != "rawjson" && output != "table" {
		log.Fatalf("invalid output format %q, only 'rawjson' and 'table' are supported", output)
	}

	cli := goclient.NewHTTP(mothershipURL, token)

	if output == "rawjson" {
		b, err := util.ListClustersRaw(cli)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Println(string(b))
		return
	}

	rs, err := util.ListClusters(cli)
	if err != nil {
		log.Fatal(err)
	}

	log.Printf("fetched %d clusters from mothership API", len(rs))

	eksAPIs := make(map[string]*aws_eks_v2.Client)
	colums := []string{"name", "provider", "region", "git-ref", "state", "eks k8s version", "eks status", "eks health"}

	stsID, err := aws.GetCallerIdentity()
	if err != nil {
		log.Printf("no AWS access -- skipping AWS API call, setting select-kubeconfig to false (%v)", err)
		colums = []string{"name", "provider", "region", "git-ref", "state"}

		// connecting to EKS requires AWS session
		selectKubeconfig = false
	} else {
		log.Printf("inspecting AWS resources using %v", *stsID.Arn)
		for _, c := range rs {
			if c.Spec.Region == "" {
				log.Printf("cluster %q spec may be outdated -- region is not populated, default to us-east-1", c.Name)
				c.Spec.Region = "us-east-1"
			}
			if _, ok := eksAPIs[c.Spec.Region]; ok {
				continue
			}
			cfg, err := aws.New(&aws.Config{
				DebugAPICalls: false,
				Region:        c.Spec.Region,
			})
			if err != nil {
				log.Panicf("failed to create AWS session %v", err)
			}
			eksAPI := aws_eks_v2.NewFromConfig(cfg)
			eksAPIs[c.Spec.Region] = eksAPI
		}
	}

	rows := make([][]string, 0, len(rs))
	promptOptions := make([]string, 0, len(rs))
	for _, c := range rs {
		if c.Status.State == v1alpha1.ClusterStateFailed {
			log.Printf("skipping failed state cluster %q", c.Spec.Name)
			continue
		}

		eksAPI, ok := eksAPIs[c.Spec.Region]
		if !ok { // no aws access
			rows = append(rows, []string{c.Spec.Name, c.Spec.Provider, c.Spec.Region, c.Spec.GitRef, string(c.Status.State)})
			continue
		}

		ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
		eksOut, err := eksAPI.DescribeCluster(ctx, &aws_eks_v2.DescribeClusterInput{
			Name: &c.Spec.Name,
		})
		cancel()

		version := "UNKNOWN"
		status := "UNKNOWN"
		health := "OK"
		if err != nil {
			if eks.IsErrClusterDeleted(err) {
				status = "DELETED/NOT FOUND"
				health = "DELETED/NOT FOUND"
			} else {
				log.Panicf("failed to describe EKS cluster %q %v", c.Name, err)
			}
		} else {
			version, status, health = eks.GetClusterStatus(eksOut)
		}

		rows = append(rows, []string{c.Spec.Name, c.Spec.Provider, c.Spec.Region, c.Spec.GitRef, string(c.Status.State), version, status, health})
		promptOptions = append(promptOptions,
			fmt.Sprintf("%s (provider %s region %s, state %s, eks status %s)",
				c.Spec.Name,
				c.Spec.Provider,
				c.Spec.Region,
				string(c.Status.State),
				status,
			))
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(colums)
	tb.AppendBulk(rows)
	tb.Render()
	fmt.Println(buf.String())

	if !selectKubeconfig {
		return
	}

	prompt := promptui.Select{
		Label: "Select the cluster you would like to connect!",
		Items: promptOptions,
	}
	idx, answer, err := prompt.Run()
	if err != nil {
		panic(err)
	}

	log.Printf("downloading kubeoconfig for %s", answer)
	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	cl, err := eks.GetCluster(ctx, rs[idx].Spec.Region, eksAPIs[rs[idx].Spec.Region], rs[idx].Spec.Name)
	cancel()
	if err != nil {
		panic(err)
	}

	ks, err := cl.Kubeconfig()
	if err != nil {
		panic(err)
	}

	fmt.Println()
	fmt.Println(ks)
}
