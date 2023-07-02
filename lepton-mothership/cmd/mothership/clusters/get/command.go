// Package get implements get command.
package get

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get all the clusters (either EKS/*)",
		Run:   getFunc,
	}
	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
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

	cfg, err := aws.New(&aws.Config{
		// TODO: make these configurable, or derive from cluster spec
		DebugAPICalls: false,
		Region:        "us-east-1",
	})
	if err != nil {
		log.Panicf("failed to create AWS session %v", err)
	}
	eksAPI := aws_eks_v2.NewFromConfig(cfg)

	colums := []string{"name", "provider", "region", "git-ref", "state", "eks k8s version", "eks status", "eks health"}
	rows := make([][]string, 0, len(rs))
	for _, c := range rs {
		ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
		eksOut, err := eksAPI.DescribeCluster(ctx, &aws_eks_v2.DescribeClusterInput{
			Name: &c.Name,
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

		rows = append(rows, []string{c.GetName(), c.Spec.Provider, c.Spec.Region, c.Spec.GitRef, string(c.Status.State), version, status, health})
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
