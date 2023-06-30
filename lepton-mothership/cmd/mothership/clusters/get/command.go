// Package get implements get command.
package get

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	"github.com/aws/aws-sdk-go/aws/awserr"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/go-pkg/aws"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
)

var (
	mothershipURL string
	token         string
	tokenPath     string
)

var (
	homeDir, _       = os.UserHomeDir()
	defaultTokenPath = filepath.Join(homeDir, ".mothership", "token")
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get all the clusters (either EKS/*)",
		Run:   clustersFunc,
	}
	cmd.PersistentFlags().StringVarP(&mothershipURL, "mothership-url", "u", "https://mothership.cloud.lepton.ai/api/v1/clusters", "Mothership API endpoint URL")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call (overwrites --token-path)")
	cmd.PersistentFlags().StringVarP(&tokenPath, "token-path", "p", defaultTokenPath, "File path that contains the beaer token for API call (to be overwritten by non-empty --token)")
	return cmd
}

func clustersFunc(cmd *cobra.Command, args []string) {
	if token == "" {
		log.Printf("empty --token, fallback to default token-path %q", defaultTokenPath)
		b, err := os.ReadFile(tokenPath)
		if err != nil {
			log.Fatalf("failed to read token file %v", err)
		}
		token = string(b)
	}

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

	colums := []string{"name", "provider", "region", "eks k8s version", "eks status", "eks health"}
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
			if isEKSDeleted(err) {
				status = "DELETED"
				health = "DELETED"
			} else {
				log.Panicf("failed to describe EKS cluster %q %v", c.Name, err)
			}
		} else {
			version = *eksOut.Cluster.Version
			status = string(eksOut.Cluster.Status)
			if eksOut.Cluster.Health != nil && eksOut.Cluster.Health.Issues != nil && len(eksOut.Cluster.Health.Issues) > 0 {
				health = fmt.Sprintf("%+v", eksOut.Cluster.Health.Issues)
			}
		}

		rows = append(rows, []string{c.GetName(), c.Spec.Provider, c.Spec.Region, version, status, health})
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

func isEKSDeleted(err error) bool {
	if err == nil {
		return false
	}
	awsErr, ok := err.(awserr.Error)
	if ok && awsErr.Code() == "ResourceNotFoundException" &&
		strings.HasPrefix(awsErr.Message(), "No cluster found for") {
		return true
	}
	// ResourceNotFoundException: No cluster found for name: aws-k8s-tester-155468BC717E03B003\n\tstatus code: 404, request id: 1e3fe41c-b878-11e8-adca-b503e0ba731d
	return strings.Contains(err.Error(), "No cluster found for name: ")
}
