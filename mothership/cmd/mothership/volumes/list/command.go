// Package list implements list command.
package list

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	efs "github.com/leptonai/lepton/go-pkg/aws/efs"

	"github.com/spf13/cobra"
)

var (
	volumeKinds []string
	region      string
	provider    string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all volumes",
		Run:   listFunc,
	}
	cmd.PersistentFlags().StringSliceVar(&volumeKinds, "volume-kinds", []string{"efs"}, "Volume kinds to list")
	cmd.PersistentFlags().StringVarP(&region, "region", "r", "us-east-1", "AWS region to query")

	// TODO: support other providers
	cmd.PersistentFlags().StringVarP(&provider, "provider", "p", "aws", "Provider to check the quota")

	return cmd
}

func listFunc(cmd *cobra.Command, args []string) {
	for _, kind := range volumeKinds {
		switch kind {
		case "ebs":
			if provider != "aws" {
				log.Fatal("volume kind ebs only valid for aws")
			}
			log.Fatal("not implemented")

		case "efs":
			if provider != "aws" {
				log.Fatal("volume kind ebs only valid for aws")
			}

			cfg, err := aws.New(&aws.Config{
				DebugAPICalls: false,
				Region:        region,
			})
			if err != nil {
				log.Panicf("failed to create AWS session %v", err)
			}

			ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
			fss, err := efs.ListFileSystems(ctx, cfg)
			cancel()
			if err != nil {
				log.Fatalf("failed to list EFS file systems %v", err)
			}
			for i, fs := range fss {
				fmt.Printf("###\nFile sytem #%02d\n\n", i+1)
				fmt.Println(fs.String())
			}
		}
	}
}
