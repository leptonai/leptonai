package common

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"

	"github.com/leptonai/lepton/go-pkg/aws/aurora"
	"github.com/spf13/cobra"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

var (
	homeDir, _       = os.UserHomeDir()
	DefaultTokenPath = filepath.Join(homeDir, ".mothership", "token")
)

func ReadAuroraConfigFromFlag(cmd *cobra.Command) aurora.AuroraConfig {
	auroraCfgFlag := cmd.Flag("aurora-config").Value.String()
	useCfg, _ := strconv.ParseBool(auroraCfgFlag)
	if !useCfg {
		log.Println("reading aurora config from provided flags")
		if cmd.Flag("db-host").Value.String() == "" {
			log.Fatal("db-host flag is empty")
		}
		if cmd.Flag("db-user").Value.String() == "" {
			log.Fatal("db-user flag is empty")
		}

		dbHost := cmd.Flag("db-host").Value.String()
		dbPort, _ := strconv.Atoi(cmd.Flag("db-port").Value.String())

		s := cmd.Flag("auth-with-token").Value.String()
		authWithToken, _ := strconv.ParseBool(s)

		if !authWithToken && cmd.Flag("db-password").Value.String() == "" {
			log.Fatal("token auth is not enabled but db-password flag is empty")
		}
		return aurora.AuroraConfig{
			Region:        cmd.Flag("region").Value.String(),
			DBDriverName:  cmd.Flag("db-driver-name").Value.String(),
			DBName:        cmd.Flag("db-name").Value.String(),
			DBHost:        dbHost,
			DBPort:        dbPort,
			DBEndpoint:    fmt.Sprintf("%s:%d", dbHost, dbPort),
			DBUser:        cmd.Flag("db-user").Value.String(),
			DBPassword:    cmd.Flag("db-password").Value.String(),
			AuthWithToken: authWithToken,
		}
	}

	useConfigPath := aurora.DefaultAuroraPath
	b, err := os.ReadFile(useConfigPath)
	if err != nil {
		log.Fatalf("failed to read config file %v", err)
	}
	config := aurora.AuroraConfig{}
	err = json.Unmarshal(b, &config)
	if err != nil {
		log.Fatalf("failed to unmarshal config data %v", err)
	}
	return config
}

func ReadTokenFromFlag(cmd *cobra.Command) string {
	tokenFlag := cmd.Flag("token")
	tokenPathFlag := cmd.Flag("token-path")

	token := ""
	if tokenFlag != nil && tokenFlag.Value.String() != "" {
		// --token flag is not empty, so overwrites --token-path value
		token = tokenFlag.Value.String()
	}

	if token == "" {
		// --token flag is empty, so fallback to --token-path value
		// assume the default flag value is set to "DefaultTokenPath"
		// so this is never an empty string
		if tokenPathFlag == nil || tokenPathFlag.Value.String() == "" {
			log.Fatal("both --token and --token-path are empty")
		}

		tokenPath := tokenPathFlag.Value.String()
		b, err := os.ReadFile(tokenPath)
		if err != nil {
			log.Fatalf("failed to read token file %v", err)
		}

		token = string(b)
	}

	if token == "" {
		log.Fatal("no token found")
	}

	return token
}

func ReadKubeconfigFromFlag(cmd *cobra.Command) string {
	return cmd.Flag("kubeconfig").Value.String()
}

func ReadMothershipURLFromFlag(cmd *cobra.Command) string {
	return cmd.Flag("mothership-url").Value.String()
}

func BuildRestConfig(configPath string) (*rest.Config, string, error) {
	log.Printf("Loading kubeconfig %q", configPath)

	kcfg, err := clientcmd.LoadFromFile(configPath)
	if err != nil {
		return nil, "", fmt.Errorf("failed to load kubeconfig %v", err)
	}
	clusterARN := ""
	for k := range kcfg.Clusters {
		clusterARN = k
		break
	}

	restConfig, err := clientcmd.BuildConfigFromFlags("", configPath)
	if err != nil {
		return nil, "", fmt.Errorf("failed to build config from kubconfig %v", err)
	}

	return restConfig, clusterARN, nil
}

// Maps namespace to common used eks-lepton services.
var EKSLeptonServices = map[string]map[string]struct{}{
	"kubecost": {
		"cost-analyzer-cost-analyzer":     struct{}{},
		"cost-analyzer-prometheus-server": struct{}{},
	},
	"kube-prometheus-stack": {
		"kube-prometheus-stack-prometheus": struct{}{},
		"kube-prometheus-stack-grafana":    struct{}{},
	},
}
