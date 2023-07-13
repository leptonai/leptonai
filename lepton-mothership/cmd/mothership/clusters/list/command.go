// Package list implements list command.
package list

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
)

var (
	output string
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

	return cmd
}

func listFunc(cmd *cobra.Command, args []string) {
	token := common.ReadTokenFromFlag(cmd)
	mothershipURL := common.ReadMothershipURLFromFlag(cmd)
	if output != "rawjson" && output != "table" {
		log.Fatalf("invalid output format %q, only 'rawjson' and 'table' are supported", output)
	}

	cli := goclient.NewHTTP(mothershipURL, token)
	b, err := cli.RequestPath(http.MethodGet, "/clusters", nil, nil)
	if err != nil {
		log.Fatal(err)
	}

	var rs []*crdv1alpha1.LeptonCluster
	if err = json.Unmarshal(b, &rs); err != nil {
		log.Fatalf("failed to decode %v", err)
	}
	if output == "rawjson" {
		fmt.Println(string(b))
		return
	}

	log.Printf("fetched %d clusters", len(rs))

	eksAPIs := make(map[string]*aws_eks_v2.Client)
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

	colums := []string{"name", "provider", "region", "git-ref", "state", "eks k8s version", "eks status", "eks health"}
	rows := make([][]string, 0, len(rs))
	for _, c := range rs {
		eksAPI := eksAPIs[c.Spec.Region]

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
				status = "DELETED"
				health = "DELETED"
			} else {
				log.Panicf("failed to describe EKS cluster %q %v", c.Name, err)
			}
		} else {
			version, status, health = eks.GetClusterStatus(eksOut)
		}

		rows = append(rows, []string{c.Spec.Name, c.Spec.Provider, c.Spec.Region, c.Spec.GitRef, string(c.Status.State), version, status, health})
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
}
