// Package forget implements forget command.
package forget

import (
	"encoding/json"
	"log"
	"os"

	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/mothership/cmd/mothership/contexts/save"

	"github.com/spf13/cobra"
)

var (
	cpath string
	name  string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership contexts forget" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "forget",
		Short: "Forgets the mothership context",
		Run:   forgetFunc,
	}
	cmd.PersistentFlags().StringVarP(&cpath, "path", "p", common.DefaultContextPath, "Path of the directory to save the context")
	cmd.PersistentFlags().StringVarP(&name, "name", "n", "", "Name of the context to forget")

	return cmd
}

func forgetFunc(cmd *cobra.Command, args []string) {
	exists, err := util.CheckPathExists(cpath)
	if err != nil {
		log.Fatalf("failed to check path exists %v", err)
	}

	if exists {
		f, err := os.Open(cpath)
		if err != nil {
			log.Fatalf("failed to open context file %v", err)
		}
		ctxs := common.Contexts{}
		err = json.NewDecoder(f).Decode(&ctxs)
		if err != nil {
			log.Fatalf("failed to decode context file %v", err)
		}
		defer f.Close()

		delete(ctxs.Contexts, name)
		if ctxs.Current == name {
			ctxs.Current = ""
		}

		err = save.WriteAndFlush(cpath, ctxs)
		if err != nil {
			log.Fatalf("failed to update the context file %v", err)
		}

		log.Printf("deleted context for %s", name)
	} else {
		log.Fatalf("context file %q does not exist", cpath)
	}
}
