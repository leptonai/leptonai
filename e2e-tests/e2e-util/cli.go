package e2eutil

import (
	"os/exec"
)

type CliWrapper struct {
	WorkspaceURL string
	AuthToken    string
}

const cmdName = "lep"

func NewCliWrapper(workspaceURL string, authToken string) *CliWrapper {
	return &CliWrapper{
		WorkspaceURL: workspaceURL,
		AuthToken:    authToken,
	}
}

func (c *CliWrapper) Login(name string) (string, error) {
	if name == "" {
		name = c.WorkspaceURL
	}
	fullArgs := []string{"workspace", "login", "--test-only-workspace-url", c.WorkspaceURL, "-i", name, "-t", c.AuthToken}
	return c.Run(fullArgs...)
}

func (c *CliWrapper) Logout() (string, error) {
	fullArgs := []string{"workspace", "logout"}
	return c.Run(fullArgs...)
}

func (c *CliWrapper) RunRemote(object, action string, args ...string) (string, error) {
	output, err := c.Login(c.WorkspaceURL)
	if err != nil {
		return output, err
	}
	fullArgs := []string{object, action}
	fullArgs = append(fullArgs, args...)
	output, err = c.Run(fullArgs...)
	if err != nil {
		return output, err
	}
	logoutOutput, err := c.Logout()
	if err != nil {
		return logoutOutput, err
	}
	return output, nil
}

func (c *CliWrapper) RunLocal(object, action string, args ...string) (string, error) {
	fullArgs := []string{object, action}
	fullArgs = append(fullArgs, args...)
	return c.Run(fullArgs...)
}

func (c *CliWrapper) Run(args ...string) (string, error) {
	cmd := exec.Command(cmdName, args...)
	output, err := cmd.CombinedOutput()
	return string(output), err
}
