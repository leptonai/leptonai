// Package updateall implements update-all command.
package updateall

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/mothership/cmd/mothership/util"
	"github.com/leptonai/lepton/mothership/crd/api/v1alpha1"

	aws_v2 "github.com/aws/aws-sdk-go-v2/aws"
	aws_eks_v2 "github.com/aws/aws-sdk-go-v2/service/eks"
	"github.com/spf13/cobra"
	clientcmd_api_v1 "k8s.io/client-go/tools/clientcmd/api/v1"
	"sigs.k8s.io/yaml"
)

var (
	kubeconfigPath string
	awsRegions     []string

	useMothership bool
	mothershipURL string
	token         string
	tokenPath     string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership kubeconfig update-all" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "update-all",
		Short:      "Fetches all clusters and write kubeconfig for all",
		Aliases:    []string{"all", "update", "u"},
		SuggestFor: []string{"all", "update", "u"},
		Run:        updateAllFunc,
	}

	cmd.PersistentFlags().StringVarP(&kubeconfigPath, "kubeconfig", "k", "", "Kubeconfig path (otherwise, client uses the one from KUBECONFIG env var)")
	cmd.PersistentFlags().StringSliceVarP(&awsRegions, "aws-regions", "r", []string{"us-east-1", "us-west-2"}, "A set of all AWS regions to fetch clusters from")

	cmd.PersistentFlags().BoolVarP(&useMothership, "use-mothership", "m", false, "[optional] Set true to use mothership to filter out failed clusters, select existing regions (useful if you don't know which regions to query)")
	cmd.PersistentFlags().StringVarP(&mothershipURL, "mothership-url", "u", "", "[optional] Mothership API endpoint URL")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "[optional] Beaer token for API call (overwrites --token-path)")
	cmd.PersistentFlags().StringVarP(&tokenPath, "context-path", "p", common.DefaultContextPath, "[optional] Directory path that contains the context of the motership API call (to be overwritten by non-empty --token)")

	return cmd
}

func updateAllFunc(cmd *cobra.Command, args []string) {
	stsID, err := aws.GetCallerIdentity()
	if err != nil {
		log.Fatalf("failed to get caller identity %v", err)
	}
	log.Printf("logged into AWS as %q", *stsID.Arn)

	eksClusters := make([]eks.Cluster, 0)
	if useMothership {
		mctx := common.ReadContext(cmd)
		token, mothershipURL := mctx.Token, mctx.URL

		cli := goclient.NewHTTP(mothershipURL, token)
		rs, err := util.ListClusters(cli)
		if err != nil {
			log.Fatal(err)
		}

		log.Printf("inspecting %d clusters using mothership", len(rs))
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

		for _, c := range rs {
			if c.Status.State == v1alpha1.ClusterOperationalStateFailed {
				log.Printf("skipping failed state cluster %q", c.Spec.Name)
				continue
			}
			if strings.HasPrefix(c.Spec.Name, "test") {
				log.Printf("skipping test cluster %q", c.Spec.Name)
				continue
			}

			ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
			cl, err := eks.GetClusterWithClient(ctx, c.Spec.Region, eksAPIs[c.Spec.Region], c.Spec.Name)
			cancel()
			if err != nil {
				log.Fatalf("failed to get cluster %q (%v)", c.Spec.Name, err)
			}

			if cl.Status != "ACTIVE" {
				log.Printf("skipping non-active cluster %q (status %q)", cl.ARN, cl.Status)
			}
			eksClusters = append(eksClusters, cl)
		}
	} else {
		log.Printf("inspecting all clusters for AWS regions %q", awsRegions)
		awsCfgs := make(map[string]aws_v2.Config)
		for _, reg := range awsRegions {
			if _, ok := awsCfgs[reg]; ok {
				continue
			}
			cfg, err := aws.New(&aws.Config{
				DebugAPICalls: false,
				Region:        reg,
			})
			if err != nil {
				log.Panicf("failed to create AWS session %v", err)
			}
			awsCfgs[reg] = cfg
		}
		for reg, awsCfg := range awsCfgs {
			ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
			cls, err := eks.ListClusters(ctx, reg, awsCfg, -1)
			cancel()
			if err != nil {
				log.Panicf("failed to list clusters %v", err)
			}

			for _, cl := range cls {
				if cl.Status != "ACTIVE" {
					log.Printf("skipping non-active cluster %q (status %q)", cl.ARN, cl.Status)
				}
				eksClusters = append(eksClusters, cl)
			}
		}
	}

	// oldest cluster as first thus current context
	sort.SliceStable(eksClusters, func(i, j int) bool {
		return eksClusters[i].CreatedAt.Before(eksClusters[j].CreatedAt)
	})

	kcfg := clientcmd_api_v1.Config{}
	for i, cl := range eksClusters {
		kcfg2, err := cl.Kubeconfig()
		if err != nil {
			log.Fatalf("failed to get kubeconfig %v", err)
		}

		if i == 0 {
			kcfg = kcfg2
			log.Printf("using %q as current context", kcfg2.CurrentContext)
			continue
		}

		kcfg.Clusters = append(kcfg.Clusters, kcfg2.Clusters...)
		kcfg.Contexts = append(kcfg.Contexts, kcfg2.Contexts...)
		kcfg.AuthInfos = append(kcfg.AuthInfos, kcfg2.AuthInfos...)
		log.Printf("added context %q", kcfg2.CurrentContext)
	}

	kubeconfigPath := os.Getenv("KUBECONFIG")
	if kubeconfigPath == "" {
		kubeconfigPath = common.ReadKubeconfigFromFlag(cmd)
	}
	if kubeconfigPath == "" {
		hd, _ := os.UserHomeDir()
		kubeconfigPath = hd + "/.kube/config"
	}

	if _, err := os.Stat(kubeconfigPath); err == nil {
		log.Printf("overwriting kubeconfig %q", kubeconfigPath)
	}
	if err = os.MkdirAll(filepath.Dir(kubeconfigPath), 0700); err != nil {
		log.Fatalf("failed to create kubeconfig dir %q (%v)", filepath.Dir(kubeconfigPath), err)
	}

	kb, err := yaml.Marshal(kcfg)
	if err != nil {
		log.Fatalf("failed to marshal kubeconfig %v", err)
	}

	f, err := os.OpenFile(kubeconfigPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0600)
	if err != nil {
		log.Fatalf("failed to kubeconfig file %v", err)
	}
	defer f.Close()

	if _, err = f.Write(kb); err != nil {
		log.Fatalf("failed to write kubeconfig file %v", err)
	}

	log.Printf("wrote kubeconfig %q with %d clusters", kubeconfigPath, len(kcfg.Clusters))
	fmt.Println("Run following 'kubectl config use-context' commands to update your kubeconfig:")
	for _, ctx := range kcfg.Contexts {
		fmt.Printf("kubectl config use-context %q --kubeconfig %q\n", ctx.Name, kubeconfigPath)
	}
}
