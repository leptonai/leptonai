package e2eutil

import (
	"os/exec"
)

type CliWrapper struct {
	RemoteURL string
	AuthToken string
}

const cmdName = "lep"

func NewCliWrapper(remoteURL string, authToken string) *CliWrapper {
	return &CliWrapper{
		RemoteURL: remoteURL,
		AuthToken: authToken,
	}
}

func (c *CliWrapper) Login(name string) (string, error) {
	if name == "" {
		name = c.RemoteURL
	}
	fullArgs := []string{"remote", "login", "-r", c.RemoteURL, "-n", name, "-t", c.AuthToken}
	return c.Run(fullArgs...)
}

func (c *CliWrapper) Logout() (string, error) {
	fullArgs := []string{"remote", "logout"}
	return c.Run(fullArgs...)
}

func (c *CliWrapper) RunRemote(object, action string, args ...string) (string, error) {
	output, err := c.Login(c.RemoteURL)
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
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return string(output), nil
}
