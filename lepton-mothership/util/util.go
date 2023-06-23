package util

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"

	"github.com/leptonai/lepton/lepton-mothership/git"
)

const (
	leptonRepoURL = "https://github.com/leptonai/lepton.git"
)

func PrepareTerraformWorkingDir(dirName, moduleName, version string) (string, error) {
	wd, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("failed to get working directory: %s", err)
	}
	gitDir := filepath.Join(wd, dirName, "git")
	err = os.RemoveAll(gitDir)
	if err != nil {
		return "", fmt.Errorf("failed to remove git directory: %s", err)
	}
	err = os.MkdirAll(gitDir, 0750)
	if err != nil {
		return "", fmt.Errorf("failed to create git directory: %s", err)
	}

	// Optimize me: only does one clone for all clusters
	// TODO: switch to desired version of terraform code from the git repo
	err = git.Clone(gitDir, leptonRepoURL, version)
	if err != nil {
		return "", fmt.Errorf("failed to clone the git repo: %s", err)
	}
	log.Println("cloned the git repo:", leptonRepoURL)

	src := gitDir + "/charts"
	dest := gitDir + "/infra/terraform/" + moduleName + "/charts"
	err = exec.Command("cp", "-R", src, dest).Run()
	if err != nil {
		return "", fmt.Errorf("failed to copy charts to terraform directory: %s", err)
	}
	log.Println("copied charts to terraform directory")

	return gitDir + "/infra/terraform/" + moduleName, nil
}

const (
	NameInvalidMessage = "Name must consist of lower case alphanumeric characters, and must start with an alphabetical character and be no longer than 16 characters"
)

var (
	nameRegex = regexp.MustCompile("^[a-z]([a-z0-9]*)?$")
)

// ValidateName returns true if the given name is valid.
func ValidateName(name string) bool {
	return nameRegex.MatchString(name) && len(name) <= 16
}
