// Package config implements ping command.
package config

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"

	"github.com/leptonai/lepton/go-pkg/aws/aurora"
	"github.com/leptonai/lepton/go-pkg/util"

	_ "github.com/lib/pq"
	"github.com/manifoldco/promptui"
	"github.com/spf13/cobra"
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership aurora config" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "config",
		Short: "Saves Aurora config to disk",
		Long: `
# Save DB configuration data to disk, to use for other mothership commands
Usage:
mothership aurora config
`,
		Run: configFunc,
	}
	return cmd
}

func promptGetInput(label string, defaultVal string) string {
	// no validation as we allow empty input
	validate := func(input string) error {
		return nil
	}
	prompt := promptui.Prompt{
		Label:    label,
		Validate: validate,
		Default:  defaultVal,
	}
	res, err := prompt.Run()
	if err != nil {
		log.Fatalf("failed to get input %v", err)
	}
	return res
}

// ref. https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.IAMDBAuth.Connecting.Go.html#UsingWithRDS.IAMDBAuth.Connecting.GoV2
func configFunc(cmd *cobra.Command, args []string) {
	// TODO: support for custom config paths
	region := promptGetInput("Enter AWS region", aurora.DefaultRegion)
	driver := promptGetInput("Enter AWS Aurora database driver name (defaults to postgres)", aurora.DefaultDriver)
	dbName := promptGetInput("Enter AWS Aurora database name", aurora.DefaultDBName)
	dbHost := promptGetInput("Enter AWS Aurora database host", "")
	dbPortStr := promptGetInput("Enter AWS Aurora database port", fmt.Sprintf("%d", aurora.DefaultDBPort))
	dbPort, err := strconv.Atoi(dbPortStr)
	if err != nil {
		log.Fatalf("failed to convert db port to int %v", err)
	}
	dbUser := promptGetInput("Enter AWS Aurora database user", "")
	dbPassword := promptGetInput("Enter AWS Aurora database password", "")
	authWithTokenStr := promptGetInput("auth with token?", "false")
	authWithToken, err := strconv.ParseBool(authWithTokenStr)
	if err != nil {
		log.Fatalf("failed to convert auth with token to bool %v", err)
	}

	auroraCfg := aurora.AuroraConfig{
		Region:        region,
		DBDriverName:  driver,
		DBName:        dbName,
		DBHost:        dbHost,
		DBPort:        dbPort,
		DBEndpoint:    fmt.Sprintf("%s:%d", dbHost, dbPort),
		DBUser:        dbUser,
		DBPassword:    dbPassword,
		AuthWithToken: authWithToken,
	}
	configPath := aurora.DefaultAuroraPath
	fileExists, err := util.CheckPathExists(configPath)
	if err != nil {
		log.Fatalf("failed to check path exists %v", err)
	}

	if !fileExists {
		if filepath.Dir(configPath) != "/" {
			if err := os.MkdirAll(filepath.Dir(configPath), 0777); err != nil {
				log.Fatal(err)
			}
		}
	}

	f, err := os.Create(configPath)
	if err != nil {
		log.Fatalf("failed to create file %v", err)
	}
	defer f.Close()

	d, err := json.Marshal(auroraCfg)
	if err != nil {
		log.Fatalf("failed to marshal config %v", err)
	}
	_, err = f.Write(d)
	if err != nil {
		log.Fatalf("failed to write config %v", err)
	}
}
