package helm

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
)

func Install(chartPath, releaseName, namespace string, overrides map[string]interface{}) error {
	overridesJSON, err := json.Marshal(overrides)
	if err != nil {
		return fmt.Errorf("failed to marshal overrides to JSON: %w", err)
	}

	cmd := exec.Command("helm", "install", releaseName, chartPath, "--namespace", namespace, "--set-json", string(overridesJSON), "--create-namespace")

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err = cmd.Run()
	if err != nil {
		return fmt.Errorf("failed to run helm install command: %w", err)
	}

	return nil
}

func Uninstall(releaseName string) error {
	cmd := exec.Command("helm", "uninstall", releaseName)

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		return fmt.Errorf("failed to run helm uninstall command: %w", err)
	}

	return nil
}

func Upgrade(chartPath, releaseName, namespace string, overrides map[string]interface{}) error {
	overridesJSON, err := json.Marshal(overrides)
	if err != nil {
		return fmt.Errorf("failed to marshal overrides to JSON: %w", err)
	}

	cmd := exec.Command("helm", "upgrade", releaseName, chartPath, "--namespace", namespace, "--set-json", string(overridesJSON))

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err = cmd.Run()
	if err != nil {
		return fmt.Errorf("failed to run helm upgrade command: %w", err)
	}

	return nil
}
