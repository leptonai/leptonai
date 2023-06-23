package workspace

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

// Make workspace a struct and do not use global variables
var (
	DataStore = datastore.NewCRStore[*crdv1alpha1.LeptonWorkspace](
		storeNamespace,
		&crdv1alpha1.LeptonWorkspace{},
	)
)

func Init() {
	wss, err := DataStore.List()
	if err != nil {
		log.Println("failed to list wss:", err)
		return
	}

	for _, item := range wss {
		ws := item

		switch ws.Status.State {
		case crdv1alpha1.WorkspaceStateCreating, crdv1alpha1.WorkspaceStateUnknown:
			go func() {
				log.Println("restart creating workspace:", ws.Spec.Name)
				// call the idempotent create function
				_, err := idempotentCreate(ws)
				if err != nil {
					log.Printf("init: failed to create workspace %s: %v", ws.Spec.Name, err)
				}
			}()
		case crdv1alpha1.WorkspaceStateUpdating:
			go func() {
				log.Println("restart updating workspace:", ws.Spec.Name)
				_, err := Update(ws.Spec)
				if err != nil {
					log.Printf("init: failed to update workspace %s: %v", ws.Spec.Name, err)
				}
			}()
		case crdv1alpha1.WorkspaceStateDeleting:
			go func() {
				log.Println("restart deleting workspace:", ws.Spec.Name)
				err := Delete(ws.Spec.Name, true)
				if err != nil {
					log.Printf("init: failed to delete workspace %s: %v", ws.Spec.Name, err)
				}
			}()
		}
	}
}

func Create(spec crdv1alpha1.LeptonWorkspaceSpec) (*crdv1alpha1.LeptonWorkspace, error) {
	workspaceName := spec.Name
	if !util.ValidateName(workspaceName) {
		return nil, fmt.Errorf("invalid workspace name %s: %s", workspaceName, util.NameInvalidMessage)
	}

	ws := &crdv1alpha1.LeptonWorkspace{
		Spec: spec,
	}
	if ws.Spec.ImageTag == "" {
		ws.Spec.ImageTag = "latest"
	}

	// TODO: data race: if another call concurrently creates a ws with the same name under
	// a different cluster, then the cluster will be updated with the new ws name while the
	// ws is not created.
	_, err := DataStore.Get(workspaceName)
	if err == nil {
		return nil, fmt.Errorf("workspace %s already exists", workspaceName)
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
	cl.Status.Workspaces = append(cl.Status.Workspaces, workspaceName)
	if err := cluster.DataStore.UpdateStatus(cl.Name, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster: %w", err)
	}

	if err := DataStore.Create(workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to create workspace: %w", err)
	}
	ws.Status = crdv1alpha1.LeptonWorkspaceStatus{
		State:     crdv1alpha1.WorkspaceStateCreating,
		UpdatedAt: uint64(time.Now().Unix()),
	}
	if err := DataStore.UpdateStatus(workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to update workspace status: %w", err)
	}

	return idempotentCreate(ws)
}

func Update(spec crdv1alpha1.LeptonWorkspaceSpec) (*crdv1alpha1.LeptonWorkspace, error) {
	workspaceName := spec.Name
	if !util.ValidateName(workspaceName) {
		return nil, fmt.Errorf("invalid workspace name %s: %s", workspaceName, util.NameInvalidMessage)
	}

	ws, err := DataStore.Get(workspaceName)
	if err != nil {
		return nil, fmt.Errorf("failed to get workspace: %w", err)
	}
	if ws.Status.State != crdv1alpha1.WorkspaceStateReady {
		log.Println("Updating a non-ready workspace...")
	}
	ws.Spec = spec
	if ws.Spec.ImageTag == "" {
		ws.Spec.ImageTag = "latest"
	}
	if err := DataStore.Update(workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to update workspace: %w", err)
	}
	ws.Status.State = crdv1alpha1.WorkspaceStateUpdating
	ws.Status.UpdatedAt = uint64(time.Now().Unix())
	if err := DataStore.UpdateStatus(workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to update workspace status: %w", err)
	}

	err = createOrUpdateWorkspace(ws)
	if err != nil {
		return nil, err
	}

	return ws, nil
}

func Delete(workspaceName string, deleteWorkspace bool) error {
	ws, err := DataStore.Get(workspaceName)
	if err != nil {
		return fmt.Errorf("failed to get workspace: %w", err)
	}

	ws.Status.State = crdv1alpha1.WorkspaceStateDeleting
	if err := DataStore.UpdateStatus(workspaceName, ws); err != nil {
		return fmt.Errorf("failed to update workspace status: %w", err)
	}

	defer func() {
		if err != nil {
			log.Println("failed to delete workspace:", err)
		} else {
			log.Println("deleted workspace:", workspaceName)
			err = DataStore.Delete(workspaceName)
			if err != nil {
				log.Println("failed to delete workspace from the data store:", err)
			}
		}
	}()

	_, err = terraform.GetWorkspace(terraformWorkspaceName(ws.Spec.ClusterName, workspaceName))
	if err != nil {
		// TODO: check if workspace does not exist. If it does not exist, then it is already deleted.
		return fmt.Errorf("failed to get workspace: %w", err)
	}

	dir, err := util.PrepareTerraformWorkingDir(terraformWorkspaceName(ws.Spec.ClusterName, workspaceName), "workspace", ws.Spec.Version)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	command := "sh"
	args := []string{"-c", "cd " + dir + " && ./uninstall.sh"}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "CLUSTER_NAME="+ws.Spec.ClusterName, "TF_API_TOKEN="+terraform.TempToken, "WORKSPACE_NAME="+workspaceName)

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
		err := terraform.DeleteEmptyWorkspace(terraformWorkspaceName(ws.Spec.ClusterName, workspaceName))
		if err != nil {
			return fmt.Errorf("failed to delete terraform workspace: %w", err)
		}
		log.Println("deleted terraform workspace:", workspaceName)
	}
	return nil
}

func List() ([]*crdv1alpha1.LeptonWorkspace, error) {
	wss, err := DataStore.List()
	if err != nil {
		return nil, fmt.Errorf("failed to list workspaces: %w", err)
	}
	return wss, nil
}

func Get(workspaceName string) (*crdv1alpha1.LeptonWorkspace, error) {
	ws, err := DataStore.Get(workspaceName)
	if err != nil {
		return nil, fmt.Errorf("failed to get workspace: %w", err)
	}
	return ws, nil
}

func idempotentCreate(ws *crdv1alpha1.LeptonWorkspace) (*crdv1alpha1.LeptonWorkspace, error) {
	var err error
	workspaceName := ws.Spec.Name

	err = terraform.CreateWorkspace(terraformWorkspaceName(ws.Spec.ClusterName, workspaceName))
	if err != nil {
		if !strings.Contains(err.Error(), "already exists") {
			return nil, fmt.Errorf("failed to create terraform workspace: %w", err)
		} else {
			log.Println("skip terraform workspace creation: already exists")
		}
	} else {
		log.Println("created terraform workspace:", workspaceName)
	}

	err = createOrUpdateWorkspace(ws)
	if err != nil {
		return nil, err
	}

	return ws, nil
}

func createOrUpdateWorkspace(ws *crdv1alpha1.LeptonWorkspace) error {
	workspaceName := ws.Spec.Name
	var err error

	defer func() {
		if err != nil {
			ws.Status.State = crdv1alpha1.WorkspaceStateFailed
		} else {
			ws.Status.State = crdv1alpha1.WorkspaceStateReady
		}
		ws.Status.UpdatedAt = uint64(time.Now().Unix())
		derr := DataStore.UpdateStatus(workspaceName, ws)
		if err == nil && derr != nil {
			log.Println("failed to update workspace state in the data store:", err)
			err = derr
		}
	}()

	var cl *crdv1alpha1.LeptonCluster
	cl, err = cluster.DataStore.Get(ws.Spec.ClusterName)
	if err != nil {
		return fmt.Errorf("failed to get cluster: %w", err)
	}
	oidcID := cl.Status.Properties.OIDCID

	dir, err := util.PrepareTerraformWorkingDir(terraformWorkspaceName(ws.Spec.ClusterName, workspaceName), "workspace", ws.Spec.Version)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	command := "sh"
	args := []string{"-c", "cd " + dir + " && ./install.sh"}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(),
		"CLUSTER_NAME="+ws.Spec.ClusterName,
		"TF_API_TOKEN="+terraform.TempToken,
		"WORKSPACE_NAME="+workspaceName,
		"IMAGE_TAG="+ws.Spec.ImageTag,
		"API_TOKEN="+ws.Spec.APIToken,
		"OIDC_ID="+oidcID,
		"WEB_ENABLED="+strconv.FormatBool(ws.Spec.EnableWeb),
		"CREATE_EFS=true",
		"VPC_ID="+cl.Status.Properties.VPCID,
		"EFS_MOUNT_TARGETS="+efsMountTargets(cl.Status.Properties.VPCPublicSubnets),
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

func terraformWorkspaceName(clusterName, workspaceName string) string {
	return clusterName + "-" + workspaceName
}

func efsMountTargets(privateSubnets []string) string {
	var sb strings.Builder
	sb.WriteString("{")
	for i, subnet := range privateSubnets {
		sb.WriteString(fmt.Sprintf(`"az-%d"={"subnet_id"="%s"}`, i, subnet))
		if i < len(privateSubnets)-1 {
			sb.WriteString(",")
		}
	}
	sb.WriteString("}")
	return sb.String()
}
