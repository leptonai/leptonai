package cluster

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/leptonai/lepton/go-pkg/datastore"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
	"github.com/leptonai/lepton/lepton-mothership/util"
)

const storeNamespace = "default"

// Make cluster a struct and do not use global variables
var (
	DataStore = datastore.NewCRStore[*crdv1alpha1.LeptonCluster](
		storeNamespace,
		&crdv1alpha1.LeptonCluster{},
	)
)

func Init() {
	clusters, err := DataStore.List()
	if err != nil {
		log.Println("failed to list clusters:", err)
		return
	}

	for _, item := range clusters {
		cl := item

		switch cl.Status.State {
		case crdv1alpha1.ClusterStateCreating, crdv1alpha1.ClusterStateUnknown:
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
				err := Delete(cl.Spec.Name, true)
				if err != nil {
					log.Printf("init: failed to delete cluster %s: %v", cl.Spec.Name, err)
				}
			}()
		}
	}
}

func Create(spec crdv1alpha1.LeptonClusterSpec) (*crdv1alpha1.LeptonCluster, error) {
	clusterName := spec.Name
	if !util.ValidateName(clusterName) {
		return nil, fmt.Errorf("invalid workspace name %s: %s", clusterName, util.NameInvalidMessage)
	}

	cl := &crdv1alpha1.LeptonCluster{
		Spec: spec,
	}
	if err := DataStore.Create(clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to create cluster: %w", err)
	}
	cl.Status = crdv1alpha1.LeptonClusterStatus{
		State:     crdv1alpha1.ClusterStateCreating,
		UpdatedAt: uint64(time.Now().Unix()),
	}
	if err := DataStore.UpdateStatus(clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster status: %w", err)
	}

	return idempotentCreate(cl)
}

func Update(spec crdv1alpha1.LeptonClusterSpec) (*crdv1alpha1.LeptonCluster, error) {
	clusterName := spec.Name
	if !util.ValidateName(clusterName) {
		return nil, fmt.Errorf("invalid workspace name %s: %s", clusterName, util.NameInvalidMessage)
	}

	cl, err := DataStore.Get(clusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get cluster: %w", err)
	}
	if cl.Status.State != crdv1alpha1.ClusterStateReady {
		log.Println("Updating a non-ready cluster...")
	}
	cl.Spec = spec
	if err := DataStore.Update(clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster: %w", err)
	}
	cl.Status.State = crdv1alpha1.ClusterStateUpdating
	cl.Status.UpdatedAt = uint64(time.Now().Unix())
	if err := DataStore.UpdateStatus(clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster status: %w", err)
	}

	err = createOrUpdateCluster(cl)
	if err != nil {
		return nil, err
	}

	return cl, nil
}

func Delete(clusterName string, deleteWorkspace bool) error {
	cl, err := DataStore.Get(clusterName)
	if err != nil {
		return fmt.Errorf("failed to get cluster: %w", err)
	}

	cl.Status.State = crdv1alpha1.ClusterStateDeleting
	if err := DataStore.UpdateStatus(clusterName, cl); err != nil {
		return fmt.Errorf("failed to update cluster status: %w", err)
	}

	defer func() {
		if err != nil {
			log.Println("failed to delete cluster:", err)
		} else {
			log.Println("deleted cluster:", clusterName)
			err = DataStore.Delete(clusterName)
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

	err = util.PrepareTerraformWorkingDir(clusterName, "eks-lepton", cl.Spec.Version)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	command := "./uninstall.sh"
	args := []string{}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+clusterName, "TF_API_TOKEN="+terraform.TempToken)

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
		err := terraform.DeleteEmptyWorkspace(clusterName)
		if err != nil {
			return fmt.Errorf("failed to delete terraform workspace: %w", err)
		}
		log.Println("deleted terraform workspace:", clusterName)
	}
	return nil
}

func List() ([]*crdv1alpha1.LeptonCluster, error) {
	cls, err := DataStore.List()
	if err != nil {
		return nil, fmt.Errorf("failed to list clusters: %w", err)
	}
	return cls, nil
}

func Get(clusterName string) (*crdv1alpha1.LeptonCluster, error) {
	cl, err := DataStore.Get(clusterName)
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

	defer func() {
		if err != nil {
			cl.Status.State = crdv1alpha1.ClusterStateFailed
		} else {
			cl.Status.State = crdv1alpha1.ClusterStateReady
		}
		cl.Status.UpdatedAt = uint64(time.Now().Unix())
		derr := DataStore.UpdateStatus(clusterName, cl)
		if err == nil && derr != nil {
			log.Println("failed to update cluster state in the data store:", err)
			err = derr
		}
	}()

	err = util.PrepareTerraformWorkingDir(clusterName, "eks-lepton", cl.Spec.Version)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	command := "./install.sh"
	args := []string{}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+clusterName, "TF_API_TOKEN="+terraform.TempToken)
	var output []byte
	output, err = cmd.CombinedOutput()
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

	// extract necessary information from the output
	// TODO: clean up the code
	cmd = exec.Command("./output.sh")
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+clusterName, "TF_API_TOKEN="+terraform.TempToken)
	output, err = cmd.CombinedOutput()
	log.Println(string(output))
	if err != nil {
		return fmt.Errorf("failed to check json output: %s", err)
	}
	exitCode = cmd.ProcessState.ExitCode()
	if exitCode != 0 {
		return fmt.Errorf("check json output exited with non-zero exit code: %d", exitCode)
	}
	err = json.Unmarshal(output, &cl.Status.Properties)
	if err != nil {
		return fmt.Errorf("failed to unmarshal json output: %s", err)
	}

	err = DataStore.UpdateStatus(clusterName, cl)
	if err != nil {
		return fmt.Errorf("failed to update cluster state in the data store: %w", err)
	}

	return nil
}
