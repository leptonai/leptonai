// Package save implements save command.
package save

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"

	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-mothership/cmd/mothership/common"

	"github.com/spf13/cobra"
)

var (
	cpath     string
	token     string
	name      string
	url       string
	overwrite bool
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership contexts save" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "save",
		Short: "Saves the mothership context",
		Run:   saveFunc,
	}
	cmd.PersistentFlags().StringVarP(&cpath, "path", "p", common.DefaultContextPath, "Directory path to save the context")
	cmd.PersistentFlags().StringVarP(&name, "name", "n", "", "Name of the context to save")
	cmd.PersistentFlags().StringVarP(&url, "url", "u", "", "URL of the mothership of the context to save")
	cmd.PersistentFlags().StringVarP(&token, "token", "t", "", "Beaer token for API call")

	cmd.PersistentFlags().BoolVarP(&overwrite, "overwrite", "o", false, "true to overwrite if exists")
	return cmd
}

func saveFunc(cmd *cobra.Command, args []string) {
	fileExists, err := util.CheckPathExists(cpath)
	if err != nil {
		log.Fatalf("failed to check path exists %v", err)
	}

	var f *os.File
	ctxs := common.Contexts{
		Contexts: map[string]common.Context{},
	}
	if !fileExists {
		if filepath.Dir(cpath) != "/" {
			if err := os.MkdirAll(filepath.Dir(cpath), 0777); err != nil {
				log.Fatal(err)
			}
		}
		f, err = os.Create(cpath)
		if err != nil {
			log.Fatalf("failed to create context file %v", err)
		}
		defer f.Close()
	} else {
		f, err := os.Open(cpath)
		if err != nil {
			log.Fatalf("failed to open context file %v", err)
		}
		defer f.Close()
		err = json.NewDecoder(f).Decode(&ctxs)
		if err != nil {
			log.Fatalf("failed to decode context file %v", err)
		}
	}

	if _, ok := ctxs.Contexts[name]; ok && !overwrite {
		log.Fatalf("context %q already exists (use --overwrite)", name)
	}

	ctxs.Contexts[name] = common.Context{
		Name:  name,
		URL:   url,
		Token: token,
	}
	ctxs.Current = name

	err = WriteAndFlush(cpath, ctxs)
	if err != nil {
		log.Fatalf("failed to write context file %v", err)
	}
	log.Printf("context %q saved", name)
}

// WriteAndFlush writes the contexts to the given path.
func WriteAndFlush(cpath string, ctxs common.Contexts) error {
	f, err := os.Create(cpath)
	if err != nil {
		return err
	}
	defer f.Close()

	err = json.NewEncoder(f).Encode(ctxs)
	if err != nil {
		return err
	}

	return nil
}
