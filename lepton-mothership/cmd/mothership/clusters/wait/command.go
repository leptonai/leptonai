// Package wait implements wait command.
package wait

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/spf13/cobra"
)

var (
	clusterName     string
	timeoutInMinute int
	expectedState   string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters logs" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "wait",
		Short: "wait for the cluster to be in the given state",
		Run:   waitFunc,
	}
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "Name of the cluster to fetch logs for")
	cmd.PersistentFlags().IntVarP(&timeoutInMinute, "timeout", "o", 30, "Timeout in minute")
	cmd.PersistentFlags().StringVarP(&expectedState, "expected-state", "e", "ready", "Expected state of the cluster")
	return cmd
}

func waitFunc(cmd *cobra.Command, args []string) {
	token := common.ReadTokenFromFlag(cmd)
	mothershipURL := common.ReadMothershipURLFromFlag(cmd)

	if clusterName == "" {
		log.Fatal("cluster name is required")
	}

	cli := goclient.NewHTTP(mothershipURL, token)

	start := time.Now()
	for i := 0; ; i++ {
		if time.Since(start).Minutes() > float64(timeoutInMinute) {
			log.Fatalf("timeout after %d minutes", timeoutInMinute)
		}
		if i != 0 {
			log.Printf("%d: waiting for 30 seconds...", i)
			time.Sleep(30 * time.Second)
		}

		b, err := cli.RequestURL(http.MethodGet, mothershipURL+"/"+clusterName, nil, nil)
		if err != nil {
			log.Println("error sending cluster get request: ", err)
			continue
		}

		c := crdv1alpha1.LeptonCluster{}
		err = json.Unmarshal(b, &c)
		if err != nil {
			log.Printf("failed to decode %v", err)
		} else {
			if c.Status.State == crdv1alpha1.LeptonClusterState(expectedState) {
				log.Printf("workspace %q is already in state %q", clusterName, expectedState)
				return
			} else {
				log.Printf("workspace %q is not in state %q (current %q) yet", clusterName, expectedState, c.Status.State)
			}
		}
	}
}
