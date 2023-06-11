package e2eutil

import (
	"os/exec"
)

type CliWrapper struct {
	RemoteURL string
}

const cmdName = "lepton"

func NewCliWrapper(remoteURL string) *CliWrapper {
	return &CliWrapper{
		RemoteURL: remoteURL,
	}
}

func (c *CliWrapper) RunRemote(object, action string, args ...string) (string, error) {
	fullArgs := []string{object, action, "-r", c.RemoteURL}
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
