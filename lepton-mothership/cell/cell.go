package cell

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"

	"github.com/leptonai/lepton/go-pkg/datastore"
	"github.com/leptonai/lepton/lepton-mothership/cluster"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
	"github.com/leptonai/lepton/lepton-mothership/util"

	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

const storeNamespace = "default"

// Make cell a struct and do not use global variables
var (
	DataStore = datastore.NewCRStore[*crdv1alpha1.LeptonCell](
		storeNamespace,
		&crdv1alpha1.LeptonCell{},
	)
)

func Init() {
	ces, err := DataStore.List()
	if err != nil {
		log.Println("failed to list ces:", err)
		return
	}

	for _, item := range ces {
		ce := item

		switch ce.Status.State {
		case crdv1alpha1.CellStateCreating, crdv1alpha1.CellStateUnknown:
			go func() {
				log.Println("restart creating cell:", ce.Spec.Name)
				// call the idempotent create function
				_, err := idempotentCreate(ce)
				if err != nil {
					log.Printf("init: failed to create cell %s: %v", ce.Spec.Name, err)
				}
			}()
		case crdv1alpha1.CellStateUpdating:
			go func() {
				log.Println("restart updating cell:", ce.Spec.Name)
				_, err := Update(ce.Spec)
				if err != nil {
					log.Printf("init: failed to update cell %s: %v", ce.Spec.Name, err)
				}
			}()
		case crdv1alpha1.CellStateDeleting:
			go func() {
				log.Println("restart deleting cell:", ce.Spec.Name)
				err := Delete(ce.Spec.Name, true)
				if err != nil {
					log.Printf("init: failed to delete cell %s: %v", ce.Spec.Name, err)
				}
			}()
		}
	}
}

func Create(spec crdv1alpha1.LeptonCellSpec) (*crdv1alpha1.LeptonCell, error) {
	cellName := spec.Name
	if !util.ValidateName(cellName) {
		return nil, fmt.Errorf("invalid cell name %s: %s", cellName, util.NameInvalidMessage)
	}

	ce := &crdv1alpha1.LeptonCell{
		Spec: spec,
	}
	if ce.Spec.ImageTag == "" {
		ce.Spec.ImageTag = "latest"
	}

	// TODO: data race: if another call concurrently creates a ce with the same name under
	// a different cluster, then the cluster will be updated with the new ce name while the
	// ce is not created.
	_, err := DataStore.Get(cellName)
	if err == nil {
		return nil, fmt.Errorf("cell %s already exists", cellName)
	}
	if !apierrors.IsNotFound(err) {
		return nil, fmt.Errorf("unknown error: %w", err)
	}

	// TODO: Fact check: I think k8s will handle the data race here: e.g., someone stepped in
	// between Get and Update, the update will fail. Users will see the error and retry.
	cl, err := cluster.DataStore.Get(spec.ClusterName)
	if err != nil {
		return nil, fmt.Errorf("cluster %s does not exist", spec.ClusterName)
	}
	cl.Status.Cells = append(cl.Status.Cells, cellName)
	if err := cluster.DataStore.UpdateStatus(cl.Name, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster: %w", err)
	}

	if err := DataStore.Create(cellName, ce); err != nil {
		return nil, fmt.Errorf("failed to create cell: %w", err)
	}
	ce.Status = crdv1alpha1.LeptonCellStatus{
		State:     crdv1alpha1.CellStateCreating,
		UpdatedAt: uint64(time.Now().Unix()),
	}
	if err := DataStore.UpdateStatus(cellName, ce); err != nil {
		return nil, fmt.Errorf("failed to update cell status: %w", err)
	}

	return idempotentCreate(ce)
}

func Update(spec crdv1alpha1.LeptonCellSpec) (*crdv1alpha1.LeptonCell, error) {
	cellName := spec.Name
	if !util.ValidateName(cellName) {
		return nil, fmt.Errorf("invalid cell name %s: %s", cellName, util.NameInvalidMessage)
	}

	ce, err := DataStore.Get(cellName)
	if err != nil {
		return nil, fmt.Errorf("failed to get cell: %w", err)
	}
	if ce.Status.State != crdv1alpha1.CellStateReady {
		log.Println("Updating a non-ready cell...")
	}
	ce.Spec = spec
	if ce.Spec.ImageTag == "" {
		ce.Spec.ImageTag = "latest"
	}
	if err := DataStore.Update(cellName, ce); err != nil {
		return nil, fmt.Errorf("failed to update cell: %w", err)
	}
	ce.Status.State = crdv1alpha1.CellStateUpdating
	ce.Status.UpdatedAt = uint64(time.Now().Unix())
	if err := DataStore.UpdateStatus(cellName, ce); err != nil {
		return nil, fmt.Errorf("failed to update cell status: %w", err)
	}

	err = createOrUpdateCell(ce)
	if err != nil {
		return nil, err
	}

	return ce, nil
}

func Delete(cellName string, deleteWorkspace bool) error {
	ce, err := DataStore.Get(cellName)
	if err != nil {
		return fmt.Errorf("failed to get cell: %w", err)
	}

	ce.Status.State = crdv1alpha1.CellStateDeleting
	if err := DataStore.UpdateStatus(cellName, ce); err != nil {
		return fmt.Errorf("failed to update cell status: %w", err)
	}

	defer func() {
		if err != nil {
			log.Println("failed to delete cell:", err)
		} else {
			log.Println("deleted cell:", cellName)
			err = DataStore.Delete(cellName)
			if err != nil {
				log.Println("failed to delete cell from the data store:", err)
			}
		}
	}()

	_, err = terraform.GetWorkspace(workspaceName(ce.Spec.ClusterName, cellName))
	if err != nil {
		// TODO: check if workspace does not exist. If it does not exist, then it is already deleted.
		return fmt.Errorf("failed to get workspace: %w", err)
	}

	err = util.PrepareTerraformWorkingDir(workspaceName(ce.Spec.ClusterName, cellName), "cell", ce.Spec.Version)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	command := "./uninstall.sh"
	args := []string{}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+ce.Spec.ClusterName, "TF_API_TOKEN="+terraform.TempToken, "CELL_NAME="+cellName)

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
		err := terraform.DeleteEmptyWorkspace(workspaceName(ce.Spec.ClusterName, cellName))
		if err != nil {
			return fmt.Errorf("failed to delete terraform workspace: %w", err)
		}
		log.Println("deleted terraform workspace:", cellName)
	}
	return nil
}

func List() ([]*crdv1alpha1.LeptonCell, error) {
	ces, err := DataStore.List()
	if err != nil {
		return nil, fmt.Errorf("failed to list cells: %w", err)
	}
	return ces, nil
}

func Get(cellName string) (*crdv1alpha1.LeptonCell, error) {
	ce, err := DataStore.Get(cellName)
	if err != nil {
		return nil, fmt.Errorf("failed to get cell: %w", err)
	}
	return ce, nil
}

func idempotentCreate(ce *crdv1alpha1.LeptonCell) (*crdv1alpha1.LeptonCell, error) {
	var err error
	cellName := ce.Spec.Name

	err = terraform.CreateWorkspace(workspaceName(ce.Spec.ClusterName, cellName))
	if err != nil {
		if !strings.Contains(err.Error(), "already exists") {
			return nil, fmt.Errorf("failed to create terraform workspace: %w", err)
		} else {
			log.Println("skip terraform workspace creation: already exists")
		}
	} else {
		log.Println("created terraform workspace:", cellName)
	}

	err = createOrUpdateCell(ce)
	if err != nil {
		return nil, err
	}

	return ce, nil
}

func createOrUpdateCell(ce *crdv1alpha1.LeptonCell) error {
	cellName := ce.Spec.Name
	var err error

	defer func() {
		if err != nil {
			ce.Status.State = crdv1alpha1.CellStateFailed
		} else {
			ce.Status.State = crdv1alpha1.CellStateReady
		}
		ce.Status.UpdatedAt = uint64(time.Now().Unix())
		derr := DataStore.UpdateStatus(cellName, ce)
		if err == nil && derr != nil {
			log.Println("failed to update cell state in the data store:", err)
			err = derr
		}
	}()

	var cl *crdv1alpha1.LeptonCluster
	cl, err = cluster.DataStore.Get(ce.Spec.ClusterName)
	if err != nil {
		return fmt.Errorf("failed to get cluster: %w", err)
	}
	oidcID := cl.Status.Properties.OIDCID

	err = util.PrepareTerraformWorkingDir(workspaceName(ce.Spec.ClusterName, cellName), "cell", ce.Spec.Version)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	command := "./install.sh"
	args := []string{}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(),
		"CLUSTER_NAME="+ce.Spec.ClusterName,
		"TF_API_TOKEN="+terraform.TempToken,
		"CELL_NAME="+cellName,
		"IMAGE_TAG="+ce.Spec.ImageTag,
		"API_TOKEN="+ce.Spec.APIToken,
		"OIDC_ID="+oidcID,
		"WEB_ENABLED="+strconv.FormatBool(ce.Spec.EnableWeb),
		"CREATE_EFS=true",
		"EFS_MOUNT_TARGETS="+efsMountTargets(cl.Status.Properties.VPCPrivateSubnets),
	)
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

func workspaceName(clusterName, cellName string) string {
	return clusterName + "-" + cellName
}

func efsMountTargets(privateSubnets []string) string {
	var sb strings.Builder
	sb.WriteString("'mount_targets={")
	for i, subnet := range privateSubnets {
		sb.WriteString(fmt.Sprintf(`"az-%d"={"subnet_id"="%s"}`, i, subnet))
		if i < len(privateSubnets)-1 {
			sb.WriteString(",")
		}
	}
	sb.WriteString("}'")
	return sb.String()
}
