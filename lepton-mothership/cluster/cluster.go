package cluster

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/leptonai/lepton/go-pkg/datastore"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/lepton-mothership/git"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
)

const (
	leptonRepoURL = "https://github.com/leptonai/lepton.git"
)

const (
	ClusterProviderEKS = "aws-eks"
	storeNamespace     = "default"
)

type (
	CellState string
)

// Make cluster a struct and do not use global variables
var (
	ds = datastore.NewCRStore[*crdv1alpha1.LeptonCluster](
		storeNamespace,
		&crdv1alpha1.LeptonCluster{},
	)
)

func Init() {
	clusters, err := ds.List()
	if err != nil {
		log.Println("failed to list clusters:", err)
		return
	}

	for _, item := range clusters {
		cl := item

		switch cl.Status.State {
		case crdv1alpha1.ClusterStateCreating:
			go func() {
				log.Println("restart creating cluster:", cl.Spec.Name)
				// call the idempotent create function
				_, err := idempotentCreate(cl)
				if err != nil {
					log.Printf("init: failed to create cluster %s: %v", cl.Spec.Name, err)
				}
			}()
		case crdv1alpha1.ClusterStateUpdating:
			go func() {
				log.Println("restart updating cluster:", cl.Spec.Name)
				_, err := Update(cl.Spec)
				if err != nil {
					log.Printf("init: failed to update cluster %s: %v", cl.Spec.Name, err)
				}
			}()
		case crdv1alpha1.ClusterStateDeleting:
			go func() {
				log.Println("restart deleting cluster:", cl.Spec.Name)
				err := Delete(cl.Spec.Name, false)
				if err != nil {
					log.Printf("init: failed to delete cluster %s: %v", cl.Spec.Name, err)
				}
			}()
		}
	}
}

func Create(spec crdv1alpha1.LeptonClusterSpec) (*crdv1alpha1.LeptonCluster, error) {
	clusterName := spec.Name
	cl := &crdv1alpha1.LeptonCluster{
		Spec: spec,
		Status: crdv1alpha1.LeptonClusterStatus{
			State:     crdv1alpha1.ClusterStateCreating,
			UpdatedAt: uint64(time.Now().Unix()),
		},
	}

	err := ds.Create(clusterName, cl)
	if err != nil {
		return nil, fmt.Errorf("failed to create cluster: %w", err)
	}

	return idempotentCreate(cl)
}

func Update(spec crdv1alpha1.LeptonClusterSpec) (*crdv1alpha1.LeptonCluster, error) {
	clusterName := spec.Name
	cl, err := ds.Get(clusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get cluster: %w", err)
	}
	if cl.Status.State != crdv1alpha1.ClusterStateReady {
		log.Println("Updating a non-ready cluster...")
	}
	cl.Spec = spec
	cl.Status.State = crdv1alpha1.ClusterStateUpdating
	cl.Status.UpdatedAt = uint64(time.Now().Unix())

	err = createOrUpdateCluster(cl)
	if err != nil {
		return nil, err
	}

	return cl, nil
}

func Delete(clusterName string, deleteWorkspace bool) error {
	cl, err := ds.Get(clusterName)
	if err != nil {
		return fmt.Errorf("failed to get cluster: %w", err)
	}

	cl.Status.State = crdv1alpha1.ClusterStateDeleting

	defer func() {
		if err != nil {
			log.Println("failed to delete cluster:", err)
		} else {
			log.Println("deleted cluster:", clusterName)
			err = ds.Delete(clusterName)
			if err != nil {
				log.Println("failed to delete cluster from the data store:", err)
			}
		}
	}()

	_, err = terraform.GetWorkspace(clusterName)
	if err != nil {
		// TODO: check if workspace does not exist. If it does not exist, then it is already deleted.
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

func List() ([]*crdv1alpha1.LeptonCluster, error) {
	cls, err := ds.List()
	if err != nil {
		return nil, fmt.Errorf("failed to list clusters: %w", err)
	}
	return cls, nil
}

func Get(clusterName string) (*crdv1alpha1.LeptonCluster, error) {
	cl, err := ds.Get(clusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get cluster: %w", err)
	}
	return cl, nil
}

func idempotentCreate(cl *crdv1alpha1.LeptonCluster) (*crdv1alpha1.LeptonCluster, error) {
	var err error
	clusterName := cl.Spec.Name

	err = terraform.CreateWorkspace(clusterName)
	if err != nil {
		if !strings.Contains(err.Error(), "already exists") {
			return nil, fmt.Errorf("failed to create terraform workspace: %w", err)
		} else {
			log.Println("skip terraform workspace creation: already exists")
		}
	} else {
		log.Println("created terraform workspace:", clusterName)
	}

	err = createOrUpdateCluster(cl)
	if err != nil {
		return nil, err
	}

	return cl, nil
}

func createOrUpdateCluster(cl *crdv1alpha1.LeptonCluster) error {
	clusterName := cl.Spec.Name
	var err error

	err = ds.Update(clusterName, cl)
	if err != nil {
		return fmt.Errorf("failed to update cluster state in the data store: %w", err)
	}

	defer func() {
		if err != nil {
			cl.Status.State = crdv1alpha1.ClusterStateFailed
		} else {
			cl.Status.State = crdv1alpha1.ClusterStateReady
		}
		cl.Status.UpdatedAt = uint64(time.Now().Unix())
		derr := ds.Update(clusterName, cl)
		if err == nil && derr != nil {
			log.Println("failed to update cluster state in the data store:", err)
			err = derr
		}
	}()

	err = prepareWorkingDir(clusterName)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
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
		return fmt.Errorf("failed to run install: %s", err)
	}
	exitCode := cmd.ProcessState.ExitCode()
	if exitCode != 0 {
		return fmt.Errorf("install exited with non-zero exit code: %d", exitCode)
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
