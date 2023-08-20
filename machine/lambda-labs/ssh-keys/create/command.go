// Package create implements create command.
package create

import (
	"fmt"
	"log/slog"
	"os"

	openapiclient "github.com/leptonai/lepton/go-pkg/openapi/lambdalabs"
	"github.com/leptonai/lepton/machine/lambda-labs/common"

	"github.com/spf13/cobra"
)

var (
	privateKeyFile string
	publicKeyFile  string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine lambda-labs ssh-keys create" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "create",
		Short:      "Creates a Lambda Labs SSH key",
		Aliases:    []string{"add", "a", "creates", "c", "apply"},
		SuggestFor: []string{"add", "a", "creates", "c", "apply"},
		Run:        createFunc,
	}

	cmd.PersistentFlags().StringVar(&privateKeyFile, "private-key-file", common.DefaultSSHPrivateKeyPath, "Required file path to save the SSH private key")
	cmd.PersistentFlags().StringVar(&publicKeyFile, "public-key-file", common.DefaultSSHPublicKeyPath, "Required file path to save the SSH public key")

	return cmd
}

func createFunc(cmd *cobra.Command, args []string) {
	if len(args) != 1 {
		slog.Error("no key name -- requires 1 argument")
		os.Exit(1)
	}
	name := args[0]

	token, err := common.ReadToken(cmd)
	if err != nil {
		slog.Error("error reading token",
			"error", err,
		)
		os.Exit(1)
	}

	configuration := openapiclient.NewConfiguration()
	configuration.DefaultHeader["Authorization"] = "Bearer " + token
	apiClient := openapiclient.NewAPIClient(configuration)

	resp, _, err := apiClient.DefaultAPI.
		AddSSHKeyExecute(
			openapiclient.ApiAddSSHKeyRequest{}.
				AddSSHKeyRequest(openapiclient.AddSSHKeyRequest{
					Name: name,
				}),
		)
	if err != nil {
		slog.Error("error creating ssh key",
			"error", err,
		)
		os.Exit(1)
	}

	if len(resp.Data.GetPrivateKey()) == 0 {
		slog.Info("no private key found")
		return
	}

	pk := resp.Data.GetPrivateKey()
	if err := os.WriteFile(privateKeyFile, []byte(pk), 0600); err != nil {
		slog.Error("error saving ssh private key",
			"key-file", privateKeyFile,
			"error", err,
		)
		os.Exit(1)
	}

	pub := resp.Data.GetPublicKey()
	if err := os.WriteFile(publicKeyFile, []byte(pub), 0600); err != nil {
		slog.Error("error saving ssh public key",
			"key-file", publicKeyFile,
			"error", err,
		)
		os.Exit(1)
	}

	slog.Info("successfully created ssh key",
		"private-key-file", privateKeyFile,
		"public-key-file", publicKeyFile,
	)

	fmt.Printf("\n")
	fmt.Println("chmod 400", privateKeyFile)
	fmt.Println("cat", privateKeyFile)
	fmt.Println("cat", publicKeyFile)
	fmt.Printf("\n")
}
