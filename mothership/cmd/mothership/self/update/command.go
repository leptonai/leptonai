// Package update implements update command.
package update

import (
	"fmt"
	"log"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/prompt"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"

	"github.com/spf13/cobra"
)

var (
	imageTag    string
	autoApprove bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership self update" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "update",
		Short: "update a the mothership image tag",
		Run:   updateFunc,
	}
	cmd.PersistentFlags().StringVarP(&imageTag, "image-tag", "i", "", "Image tag to use for the mothership deployment")
	cmd.PersistentFlags().BoolVar(&autoApprove, "auto-approve", false, "Set to auto-approve the action without prompt (if you know what you're doing)")
	return cmd
}

func updateFunc(cmd *cobra.Command, args []string) {
	if imageTag == "" {
		log.Fatal("image tag is required")
	}

	mctx := common.ReadContext(cmd)
	token, mothershipURL := mctx.Token, mctx.URL

	if !autoApprove {
		if !prompt.IsInputYes(fmt.Sprintf("Confirm to update mothership image tag to %q via %q\n", imageTag, mothershipURL)) {
			return
		}
	}

	cli := goclient.NewHTTP(mothershipURL, token)
	b, err := cli.RequestPath(http.MethodPut, "/upgrade/"+imageTag, nil, nil)
	if err != nil {
		log.Fatal("error sending request: ", err)
	}
	fmt.Printf("successfully sent %q: %s\n", http.MethodPut, string(b))
}
