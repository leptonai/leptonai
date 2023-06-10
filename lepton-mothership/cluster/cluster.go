package cluster

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/leptonai/lepton/lepton-mothership/git"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
)

const (
	leptonRepoURL = "https://github.com/leptonai/lepton.git"
)

const (
	ClusterStateCreating = "creating"
	ClusterStateReady    = "ready"
	clusterStateFailed   = "failed"
	ClusterStateDeleting = "deleting"

	ClusterProviderEKS = "aws-eks"
)

type (
	ClusterState string
	CellState    string
)

type Cluster struct {
	Spec   ClusterSpec   `json:"spec"`
	Status ClusterStatus `json:"status"`
}

type ClusterSpec struct {
	// Name is a globally unique name of a cluster within mothership.
	Name     string `json:"name"`
	Provider string `json:"provider"`
	Region   string `json:"region"`
	// Terraform module version
	Version string `json:"version"`

	Description string `json:"description"`
}

type ClusterStatus struct {
	State ClusterState `json:"state"`
	// unix timestamp
	UpdatedAt uint64 `json:"updatedAt"`

	Cells []string `json:"cells"`
}

// TODO: save cluster state to DB
func Create(cl Cluster) (*Cluster, error) {
	clusterName := cl.Spec.Name

	err := terraform.CreateWorkspace(clusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to create terraform workspace: %w", err)
	}
	log.Println("created terraform workspace:", clusterName)

	err = prepareWorkingDir(clusterName)
	if err != nil {
		return nil, err
	}

	command := "./install.sh"
	args := []string{}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+clusterName)
	output, err := cmd.CombinedOutput()
	// TODO: Stream and only print output if there is an error
	// TODO: retry on error for a couple of times
	log.Println(string(output))
	if err != nil {
		return nil, fmt.Errorf("failed to run install: %s", err)
	}
	exitCode := cmd.ProcessState.ExitCode()
	if exitCode != 0 {
		return nil, fmt.Errorf("install exited with non-zero exit code: %d", exitCode)
	}

	// TODO: fill in status
	return &cl, nil
}

func Delete(clusterName string, deleteWorkspace bool) error {
	_, err := terraform.GetWorkspace(clusterName)
	if err != nil {
		return fmt.Errorf("failed to get workspace: %w", err)
	}

	err = prepareWorkingDir(clusterName)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	command := "./uninstall.sh"
	args := []string{}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+clusterName)

	output, err := cmd.CombinedOutput()
	// TODO: Stream and only print output if there is an error
	// TODO: retry on error for a couple of times
	log.Println(string(output))
	if err != nil {
		return fmt.Errorf("failed to run uninstall: %s", err)
	}
	exitCode := cmd.ProcessState.ExitCode()
	if exitCode != 0 {
		return fmt.Errorf("uninstall exited with non-zero exit code: %d", exitCode)
	}

	if deleteWorkspace {
		err := terraform.DeleteWorkspace(clusterName)
		if err != nil {
			return fmt.Errorf("failed to delete terraform workspace: %w", err)
		}
		log.Println("deleted terraform workspace:", clusterName)
	}
	return nil
}

func prepareWorkingDir(clusterName string) error {
	wd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("failed to get working directory: %s", err)
	}
	gitDir := filepath.Join(wd, clusterName, "git")
	err = os.RemoveAll(gitDir)
	if err != nil {
		return fmt.Errorf("failed to remove git directory: %s", err)
	}
	err = os.MkdirAll(gitDir, 0750)
	if err != nil {
		return fmt.Errorf("failed to create git directory: %s", err)
	}

	// Optimize me: only does one clone for all clusters
	// TODO: switch to desired version of terraform code from the git repo
	err = git.Clone(gitDir, leptonRepoURL)
	if err != nil {
		return fmt.Errorf("failed to clone the git repo: %s", err)
	}
	log.Println("cloned the git repo:", leptonRepoURL)

	src := gitDir + "/charts"
	dest := gitDir + "/infra/terraform/eks-lepton/charts"
	err = exec.Command("cp", "-R", src, dest).Run()
	if err != nil {
		return fmt.Errorf("failed to copy charts to terraform directory: %s", err)
	}
	log.Println("copied charts to terraform directory")

	err = os.Chdir(gitDir + "/infra/terraform/eks-lepton")
	if err != nil {
		return fmt.Errorf("failed to change directory: %s", err)
	}

	return nil
}
