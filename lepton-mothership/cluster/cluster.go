package cluster

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"time"

	chanwriter "github.com/leptonai/lepton/go-pkg/chan-writer"
	"github.com/leptonai/lepton/go-pkg/datastore"
	"github.com/leptonai/lepton/go-pkg/worker"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
	"github.com/leptonai/lepton/lepton-mothership/util"

	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

const storeNamespace = "default"

// Make cluster a struct and do not use global variables
var (
	DataStore = datastore.NewCRStore[*crdv1alpha1.LeptonCluster](
		storeNamespace,
		&crdv1alpha1.LeptonCluster{},
	)

	Worker = worker.New()
)

func Init() {
	clusters, err := DataStore.List(context.Background())
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
				_, err := Update(context.Background(), cl.Spec)
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

// Create schedules a cluster create job via "eks-lepton".
// Note that the cluster name is globally unique, guaranteed by the Kubernetes and namespace.
// A redundant cluster creation with the same name will fail.
func Create(ctx context.Context, spec crdv1alpha1.LeptonClusterSpec) (*crdv1alpha1.LeptonCluster, error) {
	clusterName := spec.Name
	if !util.ValidateName(clusterName) {
		return nil, fmt.Errorf("invalid workspace name %s: %s", clusterName, util.NameInvalidMessage)
	}

	cl := &crdv1alpha1.LeptonCluster{
		Spec: spec,
	}
	if err := DataStore.Create(ctx, clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to create cluster: %w", err)
	}
	cl.Status = crdv1alpha1.LeptonClusterStatus{
		State:     crdv1alpha1.ClusterStateCreating,
		UpdatedAt: uint64(time.Now().Unix()),
	}
	if err := DataStore.UpdateStatus(ctx, clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster status: %w", err)
	}

	return idempotentCreate(cl)
}

func Update(ctx context.Context, spec crdv1alpha1.LeptonClusterSpec) (*crdv1alpha1.LeptonCluster, error) {
	clusterName := spec.Name
	if !util.ValidateName(clusterName) {
		return nil, fmt.Errorf("invalid workspace name %s: %s", clusterName, util.NameInvalidMessage)
	}

	cl, err := DataStore.Get(ctx, clusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get cluster: %w", err)
	}
	if cl.Status.State != crdv1alpha1.ClusterStateReady {
		log.Println("Updating a non-ready cluster...")
	}
	cl.Spec = spec
	if err := DataStore.Update(ctx, clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster: %w", err)
	}
	cl.Status.State = crdv1alpha1.ClusterStateUpdating
	cl.Status.UpdatedAt = uint64(time.Now().Unix())
	if err := DataStore.UpdateStatus(ctx, clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster status: %w", err)
	}

	err = Worker.CreateJob(120*time.Minute, clusterName, func(logCh chan<- string) error {
		return createOrUpdateCluster(context.Background(), cl, logCh)
	}, func() {
		tryUpdatingStateToFailed(context.Background(), clusterName)
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create job: %w", err)
	}

	return cl, nil
}

func Delete(clusterName string, deleteWorkspace bool) error {
	return Worker.CreateJob(120*time.Minute, clusterName, func(logCh chan<- string) error {
		return delete(clusterName, deleteWorkspace, logCh)
	}, func() {
		tryUpdatingStateToFailed(context.Background(), clusterName)
	})
}

func delete(clusterName string, deleteWorkspace bool, logCh chan<- string) error {
	cl, err := DataStore.Get(context.Background(), clusterName)
	if err != nil {
		if apierrors.IsNotFound(err) {
			return nil
		}
		return fmt.Errorf("failed to get cluster: %w", err)
	}

	cl.Status.State = crdv1alpha1.ClusterStateDeleting
	if err := DataStore.UpdateStatus(context.Background(), clusterName, cl); err != nil {
		return fmt.Errorf("failed to update cluster status: %w", err)
	}

	defer func() {
		if err != nil {
			log.Println("failed to delete cluster:", err)
		} else {
			log.Println("deleted cluster:", clusterName)
			err = DataStore.Delete(context.Background(), clusterName)
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

	err = terraform.ForceUnlockWorkspace(clusterName)
	if err != nil && !strings.Contains(err.Error(), "already unlocked") {
		return fmt.Errorf("failed to force unlock workspace: %w", err)
	}

	dir, err := util.PrepareTerraformWorkingDir(clusterName, "eks-lepton", cl.Spec.GitRef)
	if err != nil {
		if !strings.Contains(err.Error(), "reference not found") {
			return fmt.Errorf("failed to prepare working dir with GitRef %s: %w", cl.Spec.GitRef, err)
		}
		// If the branch was deleted, we should still be able to delete the cluster. This is especially true when we were testing
		log.Printf("failed to prepare working dir with GitRef %s, using main", cl.Spec.GitRef)
		dir, err = util.PrepareTerraformWorkingDir(clusterName, "eks-lepton", "")
		if err != nil {
			return fmt.Errorf("failed to prepare working dir with the main GitRef: %w", err)
		}
	}

	command := "sh"
	args := []string{"-c", "cd " + dir + " && ./uninstall.sh"}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+clusterName, "TF_API_TOKEN="+terraform.TempToken)

	cw := chanwriter.New(logCh)
	cmd.Stdout = cw
	cmd.Stderr = cw
	err = cmd.Run()
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

func List(ctx context.Context) ([]*crdv1alpha1.LeptonCluster, error) {
	cls, err := DataStore.List(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to list clusters: %w", err)
	}
	return cls, nil
}

func Get(ctx context.Context, clusterName string) (*crdv1alpha1.LeptonCluster, error) {
	cl, err := DataStore.Get(ctx, clusterName)
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
		if !strings.Contains(err.Error(), "already exists") && !strings.Contains(err.Error(), "already been taken") {
			return nil, fmt.Errorf("failed to create terraform workspace: %w", err)
		} else {
			log.Println("skip terraform workspace creation: already exists")
		}
	} else {
		log.Println("created terraform workspace:", clusterName)
	}

	err = terraform.ForceUnlockWorkspace(clusterName)
	if err != nil && !strings.Contains(err.Error(), "already unlocked") {
		return nil, fmt.Errorf("failed to force unlock workspace: %w", err)
	}

	err = Worker.CreateJob(120*time.Minute, clusterName, func(logCh chan<- string) error {
		return createOrUpdateCluster(context.Background(), cl, logCh)
	}, func() {
		tryUpdatingStateToFailed(context.Background(), clusterName)
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create job: %w", err)
	}

	return cl, nil
}

func createOrUpdateCluster(ctx context.Context, cl *crdv1alpha1.LeptonCluster, logCh chan<- string) error {
	clusterName := cl.Spec.Name
	var err error

	defer func() {
		if err == nil {
			cl.Status.State = crdv1alpha1.ClusterStateReady
		}
		cl.Status.UpdatedAt = uint64(time.Now().Unix())
		derr := DataStore.UpdateStatus(ctx, clusterName, cl)
		if err == nil && derr != nil {
			log.Println("failed to update cluster state in the data store:", err)
			err = derr
		}
	}()

	dir, err := util.PrepareTerraformWorkingDir(clusterName, "eks-lepton", cl.Spec.GitRef)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	command := "sh"
	args := []string{"-c", "cd " + dir + " && ./install.sh"}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+clusterName, "TF_API_TOKEN="+terraform.TempToken)
	cw := chanwriter.New(logCh)
	cmd.Stdout = cw
	cmd.Stderr = cw
	err = cmd.Run()
	if err != nil {
		return fmt.Errorf("failed to run install: %s", err)
	}
	exitCode := cmd.ProcessState.ExitCode()
	if exitCode != 0 {
		return fmt.Errorf("install exited with non-zero exit code: %d", exitCode)
	}

	// extract necessary information from the output
	// TODO: clean up the code
	command = "sh"
	args = []string{"-c", "cd " + dir + " && ./output.sh"}

	cmd = exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+clusterName, "TF_API_TOKEN="+terraform.TempToken)
	var output []byte
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

	err = DataStore.UpdateStatus(ctx, clusterName, cl)
	if err != nil {
		return fmt.Errorf("failed to update cluster state in the data store: %w", err)
	}

	return nil
}

func tryUpdatingStateToFailed(ctx context.Context, clusterName string) {
	cl, err := DataStore.Get(ctx, clusterName)
	if err != nil {
		log.Printf("failed to get cluster %s: %s", clusterName, err)
		return
	}
	if err := updateState(ctx, cl, crdv1alpha1.ClusterStateFailed); err != nil {
		log.Printf("failed to update cluster %s state to failed: %s", clusterName, err)
	}
}

func updateState(ctx context.Context, cl *crdv1alpha1.LeptonCluster, state crdv1alpha1.LeptonClusterState) error {
	cl.Status.State = state
	cl.Status.UpdatedAt = uint64(time.Now().Unix())
	return DataStore.UpdateStatus(ctx, cl.Spec.Name, cl)
}
