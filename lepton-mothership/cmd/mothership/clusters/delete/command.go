// Package delete implements delete command.
package delete

import (
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
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

	cli := goclient.NewHTTP(mothershipURL+"/"+clusterName, token)
	b, err := cli.RequestURL(http.MethodDelete, mothershipURL+"/"+clusterName, nil, nil)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("successfully sent %q: %s\n", http.MethodDelete, string(b))
}
