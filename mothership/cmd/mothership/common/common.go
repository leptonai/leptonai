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

// Context represents the mothership context.
type Context struct {
	Name  string `json:"name"`
	URL   string `json:"url"`
	Token string `json:"token"`
}

type Contexts struct {
	Contexts map[string]Context `json:"contexts"`
	Current  string             `json:"current"`
}

var (
	homeDir, _         = os.UserHomeDir()
	DefaultContextPath = filepath.Join(homeDir, ".mothership", "context")
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

		s := cmd.Flag("auth-aurora-with-token").Value.String()
		authWithToken, _ := strconv.ParseBool(s)

		if !authWithToken && cmd.Flag("db-password").Value.String() == "" {
			log.Fatal("token auth is not enabled but db-password flag is empty")
		}
		return aurora.AuroraConfig{
			Region:        cmd.Flag("db-region").Value.String(),
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
	var useConfigPath string
	if cmd.Flag("aurora-config-path").Value.String() == "" {
		useConfigPath = aurora.DefaultAuroraPath
	} else {
		useConfigPath = cmd.Flag("aurora-config-path").Value.String()
	}
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

func ReadContext(cmd *cobra.Command) Context {
	tokenFlag := cmd.Flag("token")
	token := ""
	if tokenFlag != nil && tokenFlag.Value.String() != "" {
		// --token flag is not empty, so overwrites --token-path value
		token = tokenFlag.Value.String()
	}

	mothershipURLFlag := cmd.Flag("mothership-url")
	mothershipURL := ""
	if mothershipURLFlag != nil && mothershipURLFlag.Value.String() != "" {
		mothershipURL = mothershipURLFlag.Value.String()
	}
	if token != "" && mothershipURL != "" {
		return Context{
			Name:  "user-provided",
			URL:   mothershipURL,
			Token: token,
		}
	}

	if token == "" && mothershipURL != "" {
		log.Fatal("mothership-url flag is not empty but token flag is empty")
	}
	if token != "" && mothershipURL == "" {
		log.Fatal("token flag is not empty but mothership-url flag is empty")
	}

	contextPathFlag := cmd.Flag("context-path")
	cpath := DefaultContextPath
	if contextPathFlag != nil && contextPathFlag.Value.String() != "" {
		cpath = contextPathFlag.Value.String()
	}

	f, err := os.Open(cpath)
	if err != nil {
		log.Fatalf("failed to open context file %v", err)
	}
	defer f.Close()

	ctx := Contexts{}
	err = json.NewDecoder(f).Decode(&ctx)
	if err != nil {
		log.Fatalf("failed to decode context file %v", err)
	}

	if ctx.Current == "" || ctx.Contexts[ctx.Current] == (Context{}) {
		log.Fatalf("current context is empty or not found in context file %q", cpath)
	}

	fmt.Printf("using context %q\n", ctx.Current)

	return ctx.Contexts[ctx.Current]
}

func ReadKubeconfigFromFlag(cmd *cobra.Command) string {
	return cmd.Flag("kubeconfig").Value.String()
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
