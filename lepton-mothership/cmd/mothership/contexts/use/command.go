// Package use implements use command.
package use

import (
	"encoding/json"
	"log"
	"os"

	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/contexts/save"

	"github.com/spf13/cobra"
)

var (
	cpath string
	name  string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership contexts use" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "use",
		Short: "use the mothership context",
		Run:   useFunc,
	}
	cmd.PersistentFlags().StringVarP(&cpath, "path", "p", common.DefaultContextPath, "Directory path to save the context")
	cmd.PersistentFlags().StringVarP(&name, "name", "n", "", "Name of the context to use")
	return cmd
}

func useFunc(cmd *cobra.Command, args []string) {
	fileExists, err := util.CheckPathExists(cpath)
	if err != nil {
		log.Fatalf("failed to check path exists %v", err)
	}

	if !fileExists {
		log.Printf("name %q not found", name)
		return
	}

	f, err := os.Open(cpath)
	if err != nil {
		log.Fatalf("failed to open context file %v", err)
	}
	defer f.Close()

	ctxs := common.Contexts{
		Contexts: map[string]common.Context{},
	}
	err = json.NewDecoder(f).Decode(&ctxs)
	if err != nil {
		log.Fatalf("failed to decode context file %v", err)
	}

	if _, ok := ctxs.Contexts[name]; !ok {
		log.Printf("name %q not found", name)
		return
	}

	ctxs.Current = name

	err = save.WriteAndFlush(cpath, ctxs)
	if err != nil {
		log.Fatalf("failed to write context file %v", err)
	}
	log.Printf("use %q now", name)
}
