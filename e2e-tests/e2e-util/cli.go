package e2eutil

import (
	"net/url"
	"os/exec"
)

type CliWrapper struct {
	RemoteURL string
	authToken string
}

const cmdName = "lep"

func NewCliWrapper(remoteURL string, authToken string) *CliWrapper {
	return &CliWrapper{
		RemoteURL: remoteURL,
		authToken: authToken,
	}
}

func (c *CliWrapper) login() (string, error) {
	u, err := url.Parse(c.RemoteURL)
	if err != nil {
		return "", err
	}
	name := u.Hostname()
	fullArgs := []string{"remote", "login", "-r", c.RemoteURL, "-n", name, "-t", c.authToken}
	return c.Run(fullArgs...)
}

func (c *CliWrapper) logout() (string, error) {
	fullArgs := []string{"remote", "logout"}
	return c.Run(fullArgs...)
}

func (c *CliWrapper) RunRemote(object, action string, args ...string) (string, error) {
	_, err := c.login()
	if err != nil {
		return "", err
	}
	defer c.logout()
	fullArgs := []string{object, action}
	fullArgs = append(fullArgs, args...)
	return c.Run(fullArgs...)
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
