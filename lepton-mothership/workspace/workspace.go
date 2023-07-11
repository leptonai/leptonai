package workspace

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"

	chanwriter "github.com/leptonai/lepton/go-pkg/chan-writer"
	"github.com/leptonai/lepton/go-pkg/datastore"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/go-pkg/worker"
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

	Worker = worker.New()
)

func Init() {
	wss, err := DataStore.List(context.Background())
	if err != nil {
		util.Logger.Errorw("failed to list workspaces",
			"operation", "init",
			"error", err,
		)
		return
	}

	ctow := make(map[string][]string)

	util.Logger.Infow("start to init all workspaces")

	for _, item := range wss {
		ws := item
		ctow[ws.Spec.ClusterName] = append(ctow[ws.Spec.ClusterName], ws.Spec.Name)

		switch ws.Status.State {
		case crdv1alpha1.WorkspaceStateCreating, crdv1alpha1.WorkspaceStateUnknown:
			go func() {
				util.Logger.Infow("restart creating workspace",
					"workspace", ws.Spec.Name,
					"operation", "create",
				)

				_, err := idempotentCreate(ws)
				if err != nil {
					util.Logger.Errorw("failed to create workspace",
						"workspace", ws.Spec.Name,
						"operation", "create",
						"error", err,
					)
				}
			}()
		case crdv1alpha1.WorkspaceStateUpdating:
			go func() {
				util.Logger.Infow("restart updating workspace",
					"workspace", ws.Spec.Name,
					"operation", "update",
				)

				_, err := Update(ws.Spec)
				if err != nil {
					util.Logger.Errorw("failed to update workspace",
						"workspace", ws.Spec.Name,
						"operation", "update",
						"error", err,
					)
				}
			}()
		case crdv1alpha1.WorkspaceStateDeleting:
			go func() {
				util.Logger.Infow("restart deleting workspace",
					"workspace", ws.Spec.Name,
					"operation", "delete",
				)

				err := Delete(ws.Spec.Name, true)
				if err != nil {
					util.Logger.Errorw("failed to delete workspace",
						"workspace", ws.Spec.Name,
						"operation", "delete",
						"error", err,
					)
				}
			}()
		}
	}

	for clusterName, wss := range ctow {
		ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
		cl, err := cluster.DataStore.Get(ctx, clusterName)
		cancel()
		if err != nil {
			util.Logger.Errorw("failed to get cluster",
				"cluster", clusterName,
				"operation", "init",
				"error", err,
			)
			continue
		}
		cl.Status.Workspaces = wss
		if err := cluster.DataStore.UpdateStatus(context.Background(), cl.Name, cl); err != nil {
			util.Logger.Errorw("failed to update cluster",
				"cluster", clusterName,
				"operation", "init",
				"error", err,
			)
		}
	}

	util.Logger.Infow("finished init all workspaces")
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
	if ws.Spec.QuotaGroup == "" {
		ws.Spec.QuotaGroup = "small"
	}

	// TODO: data race: if another call concurrently creates a ws with the same name under
	// a different cluster, then the cluster will be updated with the new ws name while the
	// ws is not created.
	_, err := DataStore.Get(context.Background(), workspaceName)
	if err == nil {
		return nil, fmt.Errorf("workspace %s already exists", workspaceName)
	}
	if !apierrors.IsNotFound(err) {
		return nil, fmt.Errorf("unknown error: %w", err)
	}

	// TODO: Fact check: I think k8s will handle the data race here: e.g., someone stepped in
	// between Get and Update, the update will fail. Users will see the error and retry.
	cl, err := cluster.DataStore.Get(context.Background(), spec.ClusterName)
	if err != nil {
		return nil, fmt.Errorf("cluster %s does not exist", spec.ClusterName)
	}
	cl.Status.Workspaces = append(cl.Status.Workspaces, workspaceName)
	if err := cluster.DataStore.UpdateStatus(context.Background(), cl.Name, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster: %w", err)
	}

	if err := DataStore.Create(context.Background(), workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to create workspace: %w", err)
	}
	if err := updateState(ws, crdv1alpha1.WorkspaceStateCreating); err != nil {
		return nil, fmt.Errorf("failed to update workspace status: %w", err)
	}

	return idempotentCreate(ws)
}

func Update(spec crdv1alpha1.LeptonWorkspaceSpec) (*crdv1alpha1.LeptonWorkspace, error) {
	util.Logger.Infow("updating workspace",
		"workspace", spec.Name,
		"operation", "update",
	)

	workspaceName := spec.Name
	if !util.ValidateName(workspaceName) {
		return nil, fmt.Errorf("invalid workspace name %s: %s", workspaceName, util.NameInvalidMessage)
	}

	ws, err := DataStore.Get(context.Background(), workspaceName)
	if err != nil {
		return nil, fmt.Errorf("failed to get workspace: %w", err)
	}
	if ws.Status.State != crdv1alpha1.WorkspaceStateReady {
		util.Logger.Warnw("updating a non-ready workspace",
			"workspace", workspaceName,
			"operation", "update",
		)
	}
	ws.Spec = spec
	if ws.Spec.ImageTag == "" {
		ws.Spec.ImageTag = "latest"
	}
	if err := DataStore.Update(context.Background(), workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to update workspace: %w", err)
	}
	ws.Status.State = crdv1alpha1.WorkspaceStateUpdating
	ws.Status.UpdatedAt = uint64(time.Now().Unix())
	if err := DataStore.UpdateStatus(context.Background(), workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to update workspace status: %w", err)
	}

	err = Worker.CreateJob(30*time.Minute, workspaceName, func(logCh chan<- string) error {
		cerr := createOrUpdateWorkspace(ws, logCh)
		if cerr != nil {
			util.Logger.Errorw("failed to create or update workspace",
				"workspace", ws.Spec.Name,
				"operation", "update",
				"error", cerr,
			)
		}
		return cerr
	}, func() {
		tryUpdatingStateToFailed(workspaceName)
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create job: %w", err)
	}

	return ws, nil
}

func Delete(workspaceName string, deleteWorkspace bool) error {
	return Worker.CreateJob(30*time.Minute, workspaceName, func(logCh chan<- string) error {
		return delete(workspaceName, deleteWorkspace, logCh)
	}, func() {
		tryUpdatingStateToFailed(workspaceName)
	})
}

func delete(workspaceName string, deleteWorkspace bool, logCh chan<- string) error {
	util.Logger.Infow("deleting workspace",
		"workspace", workspaceName,
		"operation", "delete",
	)

	ws, err := DataStore.Get(context.Background(), workspaceName)
	if err != nil {
		if apierrors.IsNotFound(err) {
			return nil
		}
		return fmt.Errorf("failed to get workspace: %w", err)
	}

	ws.Status.State = crdv1alpha1.WorkspaceStateDeleting
	if err := DataStore.UpdateStatus(context.Background(), workspaceName, ws); err != nil {
		return fmt.Errorf("failed to update workspace status: %w", err)
	}

	var cl *crdv1alpha1.LeptonCluster
	cl, err = cluster.DataStore.Get(context.Background(), ws.Spec.ClusterName)
	if err != nil {
		return fmt.Errorf("failed to get cluster: %w", err)
	}

	defer func() {
		if err == nil {
			util.Logger.Infow("deleted workspace",
				"workspace", workspaceName,
				"operation", "delete",
			)

			err = DataStore.Delete(context.Background(), workspaceName)
		}
	}()

	tfws := terraformWorkspaceName(ws.Spec.ClusterName, workspaceName)

	_, err = terraform.GetWorkspace(tfws)
	if err != nil {
		// TODO: check if workspace does not exist. If it does not exist, then it is already deleted.
		return fmt.Errorf("failed to get workspace: %w", err)
	}
	dir, err := util.PrepareTerraformWorkingDir(tfws, "workspace", ws.Spec.GitRef)
	if err != nil {
		if !strings.Contains(err.Error(), "reference not found") {
			return fmt.Errorf("failed to prepare working dir with GitRef %s: %w", ws.Spec.GitRef, err)
		}

		// If the branch was deleted, we should still be able to delete the workspace. This is especially true for CI workloads.
		util.Logger.Warnw("failed to prepare working dir with GitRef, trying main",
			"workspace", workspaceName,
			"operation", "delete",
			"error", err,
		)

		dir, err = util.PrepareTerraformWorkingDir(tfws, "workspace", "")
		if err != nil {
			return fmt.Errorf("failed to prepare working dir with the main GitRef: %w", err)
		}
	}

	err = terraform.ForceUnlockWorkspace(tfws)
	if err != nil && !strings.Contains(err.Error(), "already unlocked") {
		return fmt.Errorf("failed to force unlock workspace: %w", err)
	}

	command := "sh"
	args := []string{"-c", "cd " + dir + " && ./uninstall.sh"}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(),
		"CLUSTER_NAME="+ws.Spec.ClusterName,
		"TF_API_TOKEN="+terraform.TempToken,
		"WORKSPACE_NAME="+workspaceName,
		"CREATE_EFS=true",
		"VPC_ID="+cl.Status.Properties.VPCID,
		"EFS_MOUNT_TARGETS="+efsMountTargets(cl.Status.Properties.VPCPublicSubnets),
	)

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

	cl.Status.Workspaces = goutil.RemoveString(cl.Status.Workspaces, workspaceName)

	if deleteWorkspace {
		err := terraform.DeleteEmptyWorkspace(tfws)
		if err != nil {
			return fmt.Errorf("failed to delete terraform workspace: %w", err)
		}
		util.Logger.Infow("deleted terraform workspace",
			"TerraformWorkspace", workspaceName,
			"operation", "delete",
		)
	}

	util.Logger.Infow("deleted workspace",
		"workspace", workspaceName,
		"operation", "delete",
	)

	return nil
}

func List() ([]*crdv1alpha1.LeptonWorkspace, error) {
	wss, err := DataStore.List(context.Background())
	if err != nil {
		return nil, fmt.Errorf("failed to list workspaces: %w", err)
	}
	return wss, nil
}

func Get(workspaceName string) (*crdv1alpha1.LeptonWorkspace, error) {
	return DataStore.Get(context.Background(), workspaceName)
}

func idempotentCreate(ws *crdv1alpha1.LeptonWorkspace) (*crdv1alpha1.LeptonWorkspace, error) {
	util.Logger.Infow("creating workspace",
		"workspace", ws.Spec.Name,
		"operation", "create",
	)

	var err error
	workspaceName := ws.Spec.Name

	err = terraform.CreateWorkspace(terraformWorkspaceName(ws.Spec.ClusterName, workspaceName))
	if err != nil {
		if !strings.Contains(err.Error(), "already exists") && !strings.Contains(err.Error(), "already been taken") {
			return nil, fmt.Errorf("failed to create terraform workspace: %w", err)
		} else {
			util.Logger.Infow("terraform workspace already exists",
				"TerraformWorkspace", workspaceName,
				"operation", "create",
			)
		}
	} else {
		util.Logger.Infow("created terraform workspace",
			"TerraformWorkspace", workspaceName,
			"operation", "create",
		)
	}

	err = Worker.CreateJob(30*time.Minute, workspaceName, func(logCh chan<- string) error {
		cerr := createOrUpdateWorkspace(ws, logCh)
		if cerr != nil {
			util.Logger.Errorw("failed to create or update workspace",
				"workspace", workspaceName,
				"operation", "create",
				"error", cerr,
			)
		} else {
			util.Logger.Infow("created workspace",
				"workspace", workspaceName,
				"operation", "create",
			)
		}
		return cerr
	}, func() {
		tryUpdatingStateToFailed(workspaceName)
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create job: %w", err)
	}

	return ws, nil
}

func createOrUpdateWorkspace(ws *crdv1alpha1.LeptonWorkspace, logCh chan<- string) error {
	workspaceName := ws.Spec.Name
	var err error

	defer func() {
		if err == nil {
			ws.Status.State = crdv1alpha1.WorkspaceStateReady
		}
		ws.Status.UpdatedAt = uint64(time.Now().Unix())
		derr := DataStore.UpdateStatus(context.Background(), workspaceName, ws)
		if err == nil && derr != nil {
			err = derr
		}
	}()

	var cl *crdv1alpha1.LeptonCluster
	cl, err = cluster.DataStore.Get(context.Background(), ws.Spec.ClusterName)
	if err != nil {
		return fmt.Errorf("failed to get cluster: %w", err)
	}
	oidcID := cl.Status.Properties.OIDCID

	tfws := terraformWorkspaceName(ws.Spec.ClusterName, workspaceName)
	dir, err := util.PrepareTerraformWorkingDir(tfws, "workspace", ws.Spec.GitRef)
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	err = terraform.ForceUnlockWorkspace(tfws)
	if err != nil && !strings.Contains(err.Error(), "already unlocked") {
		return fmt.Errorf("failed to force unlock workspace: %w", err)
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
		"QUOTA_GROUP="+ws.Spec.QuotaGroup,
	)
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

func tryUpdatingStateToFailed(workspaceName string) {
	ws, err := DataStore.Get(context.Background(), workspaceName)
	if err != nil {
		util.Logger.Errorw("failed to get workspace",
			"workspace", workspaceName,
			"error", err,
		)
		return
	}
	if err := updateState(ws, crdv1alpha1.WorkspaceStateFailed); err != nil {
		util.Logger.Errorw("failed to update workspace state to failed",
			"workspace", workspaceName,
			"error", err,
		)
	}
}

func updateState(ws *crdv1alpha1.LeptonWorkspace, state crdv1alpha1.LeptonWorkspaceState) error {
	ws.Status.State = state
	ws.Status.UpdatedAt = uint64(time.Now().Unix())
	return DataStore.UpdateStatus(context.Background(), ws.Spec.Name, ws)
}
