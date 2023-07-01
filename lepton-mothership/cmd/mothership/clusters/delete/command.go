// Package delete implements delete command.
package delete

import (
	"context"
	"log"
	"net/http"

	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/spf13/cobra"
)

var clusterName string

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters delete" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "delete",
		Short: "Delete the given cluster",
		Run:   deleteFunc,
	}
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "Name of the cluster to delete")
	return cmd
}

func deleteFunc(cmd *cobra.Command, args []string) {
	token := common.ReadTokenFromFlag(cmd)
	mothershipURL := common.ReadMothershipURLFromFlag(cmd)

	req, err := http.NewRequestWithContext(
		context.Background(),
		"DELETE",
		mothershipURL+"/"+clusterName,
		nil,
	)
	if err != nil {
		log.Fatalf("failed to create base query request %v", err)
	}
	req.Header.Add("Authorization", "Bearer "+token)
	log.Printf("sending DELETE to: %s", req.URL.String())

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatalf("failed http request %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		log.Fatalf("failed http request %v", resp.Status)
	}
}
