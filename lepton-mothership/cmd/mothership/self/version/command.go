// Package version implements version command.
package version

import (
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"

	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership self version" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "version",
		Short: "print the mothership server version",
		Run:   versionFunc,
	}
	return cmd
}

func versionFunc(cmd *cobra.Command, args []string) {
	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL

	cli := goclient.NewHTTP(mothershipURL, token)
	b, err := cli.RequestPath(http.MethodGet, "/info", nil, nil)
	if err != nil {
		log.Fatal("error sending request: ", err)
	}
	fmt.Println(string(b))
}
