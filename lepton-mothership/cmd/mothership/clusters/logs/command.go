// Package logs implements logs command.
package logs

import (
	"context"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
)

var (
	mothershipURL string
	token         string
	tokenPath     string
	clusterName   string
)

var (
	homeDir, _       = os.UserHomeDir()
	defaultTokenPath = filepath.Join(homeDir, ".mothership", "token")
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters logs" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "logs",
		Short: "Print logs of the give cluster",
		Run:   clustersFunc,
	}
	cmd.PersistentFlags().StringVarP(&mothershipURL, "mothership-url", "u", "https://mothership.cloud.lepton.ai/api/v1/clusters", "Mothership API endpoint URL")
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "Name of the cluster to delete")
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
		mothershipURL+"/"+clusterName+"/logs",
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
