// Package logs implements logs command.
package logs

import (
	"context"
	"io"
	"log"
	"net/http"
	"os"

	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	"github.com/spf13/cobra"
)

var (
	clusterName string
	failure     bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters logs" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "logs",
		Short: "Print logs of the give cluster",
		Run:   logsFunc,
	}
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "Name of the cluster to fetch logs for")
	cmd.PersistentFlags().BoolVarP(&failure, "failure", "f", false, "Fetch logs for failed clusters")
	return cmd
}

func logsFunc(cmd *cobra.Command, args []string) {
	if clusterName == "" {
		log.Fatal("cluster name is required")
	}

	ctx := common.ReadContext(cmd)
	token, mothershipURL := ctx.Token, ctx.URL

	url := mothershipURL + "/clusters/" + clusterName
	if failure {
		url += "/failure"
	} else {
		url += "/logs"
	}

	req, err := http.NewRequestWithContext(
		context.Background(),
		"GET",
		url,
		nil,
	)
	if err != nil {
		log.Fatalf("failed to create base query request %v", err)
	}
	req.Header.Add("Authorization", "Bearer "+token)
	log.Printf("sending logs request to: %s", req.URL.String())

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatalf("failed http request %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		log.Fatalf("failed http request %v", resp.Status)
	}
	_, err = io.Copy(os.Stdout, resp.Body)
	if err != nil {
		log.Fatalf("failed to copy logs %v", err)
	}
}
