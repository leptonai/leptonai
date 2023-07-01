// Package save implements save command.
package save

import (
	"log"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"

	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
)

var (
	path      string
	token     string
	overwrite bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership token save" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "save",
		Short: "Saves the mothership token",
		Run:   saveFunc,
	}
	cmd.PersistentFlags().StringVarP(&path, "path", "p", common.DefaultTokenPath, "File path to save the token")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call")
	cmd.PersistentFlags().BoolVarP(&overwrite, "overwrite", "o", false, "true to overwrite if exists")
	return cmd
}

func saveFunc(cmd *cobra.Command, args []string) {
	fileExists, err := util.CheckPathExists(path)
	if err != nil {
		log.Fatalf("failed to check path exists %v", err)
	}

	if !fileExists || overwrite {
		if filepath.Dir(path) != "/" {
			if err := os.MkdirAll(filepath.Dir(path), 0777); err != nil {
				log.Fatal(err)
			}
		}

		f, err := os.Create(path)
		if err != nil {
			log.Fatalf("failed to create file %v", err)
		}
		defer f.Close()

		_, err = f.Write([]byte(token))
		if err != nil {
			log.Fatalf("failed to write token %v", err)
		}
		log.Printf("wrote token to %q", path)
	} else {
		log.Printf("file %q already exists (use --overwrite)", path)
	}
}
