package util

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"

	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/mothership/git"
)

const (
	leptonRepoURL = "https://github.com/leptonai/lepton.git"
)

// PrepareTerraformWorkingDir prepares terraform directory for installation.
// Specify non-empty CRD paths to copy CRD YAML files for installation (e.g., during cluster creation).
func PrepareTerraformWorkingDir(dirName, moduleName, version string, crdSrcs ...string) (string, error) {
	gitDir, err := DeleteTerraformWorkingDir(dirName)
	if err != nil {
		return "", err
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

	goutil.Logger.Infow("Git Cloned",
		"url", leptonRepoURL,
		"version", version,
	)

	src := gitDir + "/charts"
	dest := gitDir + "/infra/terraform/" + moduleName + "/charts"
	err = exec.Command("cp", "-R", src, dest).Run()
	if err != nil {
		return "", fmt.Errorf("failed to copy charts to terraform directory: %s", err)
	}
	goutil.Logger.Infow("Copied charts to terraform directory",
		"src", src,
		"dest", dest,
	)

	dest = gitDir + "/infra/terraform/" + moduleName + "/charts/" + moduleName + "/templates/"
	if _, err := os.Stat(dest); os.IsNotExist(err) { // TODO: handle backward compatibility, will delete
		dest = gitDir + "/infra/terraform/" + moduleName + "/charts/lepton/templates/"
	}
	for _, crdSrc := range crdSrcs {
		src = gitDir + crdSrc
		err = exec.Command("cp", src, dest).Run()
		if err != nil {
			return "", fmt.Errorf("failed to copy CRD yaml files to terraform directory: %s", err)
		}
		goutil.Logger.Infow("copied CRD yaml files to terraform directory",
			"src", src,
			"dest", dest,
		)
	}

	return gitDir + "/infra/terraform/" + moduleName, nil
}

func TryDeletingTerraformWorkingDir(dirName string) {
	_, err := DeleteTerraformWorkingDir(dirName)
	if err != nil {
		goutil.Logger.Errorw("Failed to delete terraform working directory",
			"dirName", dirName,
			"err", err,
		)
	}
}

func DeleteTerraformWorkingDir(dirName string) (string, error) {
	wd, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("failed to get working directory: %s", err)
	}
	gitDir := filepath.Join(wd, dirName, "git")
	err = os.RemoveAll(gitDir)
	if err != nil {
		return "", fmt.Errorf("failed to remove git directory: %s", err)
	}
	return gitDir, nil
}

const (
	nameInvalidMessageTemplate = "%s names must only consist of lower case alphanumeric characters%s, and must start with an alphabetical character and be no longer than 20 characters"
)

var (
	ClusterNameInvalidMessage   = fmt.Sprintf(nameInvalidMessageTemplate, "Cluster", " or '-'")
	WorkspaceNameInvalidMessage = fmt.Sprintf(nameInvalidMessageTemplate, "Workspace", "")
)

var (
	nameRegexAlphanumericOnly   = regexp.MustCompile("^[a-z]([a-z0-9]*)?$")
	nameRegexDashOrAlphanumeric = regexp.MustCompile("^[a-z]([a-z0-9-]*)?$")
)

// returns true if the given name is valid.
func validateName(name string, nameRegex *regexp.Regexp) bool {
	return nameRegex.MatchString(name) && len(name) <= 20
}

func ValidateClusterName(name string) bool {
	return validateName(name, nameRegexDashOrAlphanumeric)
}

func ValidateWorkspaceName(name string) bool {
	return validateName(name, nameRegexAlphanumericOnly)
}

// as an exmaple, the main domain is the "clustername.app.lepton.ai" part of "workspacename.clustername.app.lepton.ai"
// cluster spec can specify a subdomain aliwas to replace the cluster name
func CreateSharedALBMainDomain(clusterName string, clusterSubdomain string, sharedAlbRootDomain string) string {
	sharedAlbMainDomain := clusterName + "." + sharedAlbRootDomain
	if clusterSubdomain != "" {
		sharedAlbMainDomain = clusterSubdomain + "." + sharedAlbRootDomain
	}
	return sharedAlbMainDomain
}
