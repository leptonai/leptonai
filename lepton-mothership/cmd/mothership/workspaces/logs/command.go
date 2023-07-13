// Package logs implements logs command.
package logs

import (
	"context"
	"io"
	"log"
	"net/http"
	"os"

	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/spf13/cobra"
)

var (
	workspaceName string
	failure       bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership workspaces logs" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "logs",
		Short: "Print logs of the give workspace",
		Run:   logsFunc,
	}
	cmd.PersistentFlags().StringVarP(&workspaceName, "workspace-name", "w", "", "Name of the workspace to get logs")
	cmd.PersistentFlags().BoolVarP(&failure, "failure", "f", false, "Fetch logs for failed clusters")
	return cmd
}

func logsFunc(cmd *cobra.Command, args []string) {
	if workspaceName == "" {
		log.Fatal("cluster name is required")
	}

	token := common.ReadTokenFromFlag(cmd)
	mothershipURL := common.ReadMothershipURLFromFlag(cmd)

	url := mothershipURL + "/workspaces/" + workspaceName
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
