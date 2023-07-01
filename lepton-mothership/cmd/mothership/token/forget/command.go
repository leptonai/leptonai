// Package forget implements forget command.
package forget

import (
	"log"
	"os"

	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
)

var (
	path string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership token forget" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "forget",
		Short: "Forgets the mothership token",
		Run:   forgetFunc,
	}
	cmd.PersistentFlags().StringVarP(&path, "path", "p", common.DefaultTokenPath, "File path to save the token")
	return cmd
}

func forgetFunc(cmd *cobra.Command, args []string) {
	exists, err := util.CheckPathExists(path)
	if err != nil {
		log.Fatalf("failed to check path exists %v", err)
	}
	if exists {
		if err = os.Remove(path); err != nil {
			log.Fatalf("failed to remove path %v", err)
		}
		log.Printf("deleted token file %q", path)
	} else {
		log.Printf("path %q does not exist", path)
	}
}
