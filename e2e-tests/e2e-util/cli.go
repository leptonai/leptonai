package e2eutil

import (
	"os/exec"
	"sync"
)

type CliWrapper struct {
	WorkspaceURL string
	AuthToken    string
	mu           sync.Mutex
}

const cmdName = "lep"

func NewCliWrapper(workspaceURL string, authToken string) *CliWrapper {
	return &CliWrapper{
		WorkspaceURL: workspaceURL,
		AuthToken:    authToken,
	}
}

func (c *CliWrapper) Login(name string) (string, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	return c.login(name)
}

func (c *CliWrapper) login(name string) (string, error) {
	if name == "" {
		name = c.WorkspaceURL
	}
	fullArgs := []string{"workspace", "login", "--test-only-workspace-url", c.WorkspaceURL, "-i", name, "-t", c.AuthToken}
	return c.run(fullArgs...)
}

func (c *CliWrapper) Logout() (string, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	return c.logout()
}

func (c *CliWrapper) logout() (string, error) {
	fullArgs := []string{"workspace", "logout"}
	return c.run(fullArgs...)
}

func (c *CliWrapper) RunRemote(object, action string, args ...string) (string, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	output, err := c.login(c.WorkspaceURL)
	if err != nil {
		return output, err
	}
	fullArgs := []string{object, action}
	fullArgs = append(fullArgs, args...)
	output, err = c.run(fullArgs...)
	if err != nil {
		return output, err
	}
	logoutOutput, err := c.logout()
	if err != nil {
		return logoutOutput, err
	}
	return output, nil
}

func (c *CliWrapper) RunLocal(object, action string, args ...string) (string, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	fullArgs := []string{object, action}
	fullArgs = append(fullArgs, args...)
	return c.run(fullArgs...)
}

func (c *CliWrapper) Run(args ...string) (string, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	return c.run(args...)
}

func (c *CliWrapper) run(args ...string) (string, error) {
	cmd := exec.Command(cmdName, args...)
	output, err := cmd.CombinedOutput()
	return string(output), err
}
