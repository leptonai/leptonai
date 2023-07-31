package workspace

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	chanwriter "github.com/leptonai/lepton/go-pkg/chan-writer"
	"github.com/leptonai/lepton/go-pkg/datastore"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/go-pkg/worker"
	"github.com/leptonai/lepton/mothership/cluster"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/mothership/metrics"
	"github.com/leptonai/lepton/mothership/terraform"
	"github.com/leptonai/lepton/mothership/util"

	"github.com/go-git/go-git/v5/plumbing"
	"github.com/prometheus/client_golang/prometheus"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

var (
	CertificateARN string
	RootDomain     string
)

const (
	storeNamespace = "default"

	// NOTE: adjust based on per-account EKS quota
	maxWorkspaces = 300
)

// Make workspace a struct and do not use global variables
// TODO: do we want to backup the workspaces?
var (
	DataStore = datastore.NewCRStore[*crdv1alpha1.LeptonWorkspace](
		storeNamespace,
		&crdv1alpha1.LeptonWorkspace{},
		nil,
	)

	Worker = worker.New()
)

func Init() {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()
	wss, err := DataStore.List(ctx)
	if err != nil {
		goutil.Logger.Errorw("failed to list workspaces",
			"operation", "init",
			"error", err,
		)
		return
	}
	log.Printf("listed total %d workspaces", len(wss))
	metrics.SetWorkspacesTotal(float64(len(wss)))
	go monitorTotalNumberOfWorkspaces()

	ctow := make(map[string][]string)

	goutil.Logger.Infow("start to init all workspaces")

	for _, item := range wss {
		ws := item
		ctow[ws.Spec.ClusterName] = append(ctow[ws.Spec.ClusterName], ws.Spec.Name)

		switch ws.Status.State {
		case crdv1alpha1.WorkspaceOperationalStateCreating, crdv1alpha1.WorkspaceOperationalStateUnknown:
			go func() {
				goutil.Logger.Infow("restart creating workspace",
					"workspace", ws.Spec.Name,
					"operation", "create",
				)

				ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
				defer cancel()
				_, err := idempotentCreate(ctx, ws)
				if err != nil {
					goutil.Logger.Errorw("failed to create workspace",
						"workspace", ws.Spec.Name,
						"operation", "create",
						"error", err,
					)
				}
			}()
		case crdv1alpha1.WorkspaceOperationalStateUpdating:
			go func() {
				goutil.Logger.Infow("restart updating workspace",
					"workspace", ws.Spec.Name,
					"operation", "update",
				)

				_, err := Update(ctx, ws.Spec)
				if err != nil {
					goutil.Logger.Errorw("failed to update workspace",
						"workspace", ws.Spec.Name,
						"operation", "update",
						"error", err,
					)
				}
			}()
		case crdv1alpha1.WorkspaceOperationalStateDeleting:
			go func() {
				goutil.Logger.Infow("restart deleting workspace",
					"workspace", ws.Spec.Name,
					"operation", "delete",
				)

				err := Delete(ws.Spec.Name)
				if err != nil {
					goutil.Logger.Errorw("failed to delete workspace",
						"workspace", ws.Spec.Name,
						"operation", "delete",
						"error", err,
					)
				}
			}()
		}
	}

	for clusterName, wss := range ctow {
		cl, err := cluster.DataStore.Get(ctx, clusterName)
		if err != nil {
			goutil.Logger.Errorw("failed to get cluster",
				"cluster", clusterName,
				"operation", "init",
				"error", err,
			)
			continue
		}
		cl.Status.Workspaces = wss
		if err := cluster.DataStore.UpdateStatus(ctx, cl.Name, cl); err != nil {
			goutil.Logger.Errorw("failed to update cluster",
				"cluster", clusterName,
				"operation", "init",
				"error", err,
			)
		}
	}

	goutil.Logger.Infow("finished init all workspaces")
}

// monitorTotalNumberOfWorkspaces periodically polls the data store to track the total number of workspaces.
func monitorTotalNumberOfWorkspaces() {
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGTERM, syscall.SIGINT)
	for {
		select {
		case sig := <-sigs:
			goutil.Logger.Infow("received signal", "signal", sig)
			return
		case <-time.After(5 * time.Minute):
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
			wss, err := DataStore.List(ctx)
			cancel()
			if err != nil {
				goutil.Logger.Warnw("failed to list workspaces",
					"error", err,
				)
				continue
			}
			goutil.Logger.Infow("listed total workspaces",
				"operation", "list",
				"workspaces", len(wss),
			)
			metrics.SetWorkspacesTotal(float64(len(wss)))
		}
	}
}

func Create(ctx context.Context, spec crdv1alpha1.LeptonWorkspaceSpec) (*crdv1alpha1.LeptonWorkspace, error) {
	workspaceName := spec.Name
	if !util.ValidateWorkspaceName(workspaceName) {
		return nil, fmt.Errorf("invalid workspace name %s: %s", workspaceName, util.WorkspaceNameInvalidMessage)
	}

	totalWorkspaces := metrics.GetTotalWorkspaces(prometheus.DefaultGatherer)
	log.Printf("currently total %d workspaces... creating one more", totalWorkspaces)
	if totalWorkspaces >= maxWorkspaces {
		return nil, fmt.Errorf("max workspace size limit exceeded (up to %d)", maxWorkspaces)
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
	if ws.Spec.GitRef == "" {
		ws.Spec.GitRef = string(plumbing.HEAD)
	}
	if ws.Spec.State == "" {
		ws.Spec.State = crdv1alpha1.WorkspaceStateNormal
	}
	switch ws.Spec.State {
	case crdv1alpha1.WorkspaceStateNormal:
	case crdv1alpha1.WorkspaceStatePaused:
	case crdv1alpha1.WorkspaceStateTerminated:
	default:
		return nil, fmt.Errorf("invalid workspace running state %s: must be one of normal, paused, terminated", ws.Spec.State)
	}

	if err := generateQuotaFromQuotaGroup(&ws.Spec); err != nil {
		return nil, fmt.Errorf("invalid quota setting: %w", err)
	}

	// TODO: data race: if another call concurrently creates a ws with the same name under
	// a different cluster, then the cluster will be updated with the new ws name while the
	// ws is not created.
	_, err := DataStore.Get(ctx, workspaceName)
	if err == nil {
		return nil, fmt.Errorf("workspace %s already exists", workspaceName)
	}
	if !apierrors.IsNotFound(err) {
		return nil, fmt.Errorf("unknown error: %w", err)
	}

	// TODO: Fact check: I think k8s will handle the data race here: e.g., someone stepped in
	// between Get and Update, the update will fail. Users will see the error and retry.
	cl, err := cluster.DataStore.Get(ctx, spec.ClusterName)
	if err != nil {
		return nil, fmt.Errorf("cluster %s does not exist", spec.ClusterName)
	}
	cl.Status.Workspaces = append(cl.Status.Workspaces, workspaceName)
	if err := cluster.DataStore.UpdateStatus(ctx, cl.Name, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster: %w", err)
	}

	if err := DataStore.Create(ctx, workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to create workspace: %w", err)
	}
	if err := updateState(ws, crdv1alpha1.WorkspaceOperationalStateCreating); err != nil {
		return nil, fmt.Errorf("failed to update workspace status: %w", err)
	}

	return idempotentCreate(ctx, ws)
}

func Update(ctx context.Context, spec crdv1alpha1.LeptonWorkspaceSpec) (*crdv1alpha1.LeptonWorkspace, error) {
	goutil.Logger.Infow("updating workspace",
		"workspace", spec.Name,
		"operation", "update",
	)

	workspaceName := spec.Name
	ws, err := DataStore.Get(ctx, workspaceName)
	if err != nil {
		return nil, fmt.Errorf("failed to get workspace: %w", err)
	}
	if ws.Status.State != crdv1alpha1.WorkspaceOperationalStateReady {
		goutil.Logger.Warnw("updating a non-ready workspace",
			"workspace", workspaceName,
			"operation", "update",
		)
	}
	// temporarily allow updating cluster name for testing
	if spec.ClusterName != "" {
		if _, err := cluster.DataStore.Get(ctx, spec.ClusterName); err != nil {
			if apierrors.IsNotFound(err) {
				return nil, fmt.Errorf("cluster %s does not exist", spec.ClusterName)
			}
			return nil, fmt.Errorf("failed to get cluster: %w", err)
		}
		ws.Spec.ClusterName = spec.ClusterName
	}
	// only allow updating certain fields
	if spec.ImageTag != "" {
		ws.Spec.ImageTag = spec.ImageTag
	}
	ws.Spec.APIToken = spec.APIToken
	ws.Spec.EnableWeb = spec.EnableWeb
	if spec.GitRef != "" {
		ws.Spec.GitRef = spec.GitRef
	}
	if spec.QuotaGroup != "" {
		ws.Spec.QuotaGroup = spec.QuotaGroup
		ws.Spec.QuotaCPU = spec.QuotaCPU
		ws.Spec.QuotaMemoryInGi = spec.QuotaMemoryInGi
		ws.Spec.QuotaGPU = spec.QuotaGPU
		if err := generateQuotaFromQuotaGroup(&ws.Spec); err != nil {
			return nil, fmt.Errorf("invalid quota setting: %w", err)
		}
	}
	if spec.State != "" {
		ws.Spec.State = spec.State
	}
	if ws.Spec.State == "" {
		ws.Spec.State = crdv1alpha1.WorkspaceStateNormal
	}
	switch ws.Spec.State {
	case crdv1alpha1.WorkspaceStateNormal:
	case crdv1alpha1.WorkspaceStatePaused:
	case crdv1alpha1.WorkspaceStateTerminated:
	default:
		return nil, fmt.Errorf("invalid workspace running state %s: must be one of normal, paused, terminated", ws.Spec.State)
	}

	if err := DataStore.Update(ctx, workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to update workspace: %w", err)
	}

	ws.Status.LastState = ws.Status.State
	ws.Status.State = crdv1alpha1.WorkspaceOperationalStateUpdating
	ws.Status.UpdatedAt = uint64(time.Now().Unix())
	if err := DataStore.UpdateStatus(ctx, workspaceName, ws); err != nil {
		return nil, fmt.Errorf("failed to update workspace status: %w", err)
	}

	err = Worker.CreateJob(30*time.Minute, workspaceName, func(logCh chan<- string) error {
		cerr := createOrUpdateWorkspace(metrics.NewCtxWithJobKind("update"), ws, logCh)
		if cerr != nil {
			goutil.Logger.Errorw("failed to create or update workspace",
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

// Delete deletes a workspace asynchronously
func Delete(workspaceName string) error {
	return Worker.CreateJob(30*time.Minute, workspaceName, func(logCh chan<- string) error {
		return delete(workspaceName, logCh)
	}, func() {
		tryUpdatingStateToFailed(workspaceName)
	})
}

// TODO: handle or prevent redundant delete requests (e.g. by using a lock)
func delete(workspaceName string, logCh chan<- string) (err error) {
	start := time.Now()
	defer func() {
		metrics.ObserveWorkspaceJobsLatency("delete", err == nil, time.Since(start))

		if err == nil {
			metrics.IncrementWorkspaceJobsSuccessTotal("delete")
			return
		}
		metrics.IncrementWorkspaceJobsFailureTotal("delete")
	}()

	goutil.Logger.Infow("deleting workspace",
		"workspace", workspaceName,
		"operation", "delete",
	)

	ctxBeforeTF, cancelBeforeTF := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancelBeforeTF()

	ws, err := DataStore.Get(ctxBeforeTF, workspaceName)
	if err != nil {
		if apierrors.IsNotFound(err) {
			return nil
		}
		return fmt.Errorf("failed to get workspace: %w", err)
	}

	ws.Status.LastState = ws.Status.State
	ws.Status.State = crdv1alpha1.WorkspaceOperationalStateDeleting
	if err := DataStore.UpdateStatus(ctxBeforeTF, workspaceName, ws); err != nil {
		return fmt.Errorf("failed to update workspace status: %w", err)
	}

	var cl *crdv1alpha1.LeptonCluster
	cl, err = cluster.DataStore.Get(ctxBeforeTF, ws.Spec.ClusterName)
	if err != nil {
		return fmt.Errorf("failed to get cluster: %w", err)
	}

	defer func() {
		if err == nil {
			goutil.Logger.Infow("deleted workspace",
				"workspace", workspaceName,
				"operation", "delete",
			)

			err = DataStore.Delete(context.Background(), workspaceName)
		}
	}()

	tfws := terraformWorkspaceName(workspaceName)

	_, err = terraform.GetWorkspace(ctxBeforeTF, tfws)
	if err != nil {
		// TODO: check if workspace does not exist. If it does not exist, then it is already deleted.
		return fmt.Errorf("failed to get workspace: %w", err)
	}
	dir, err := util.PrepareTerraformWorkingDir(tfws, "workspace", ws.Spec.GitRef)
	defer util.TryDeletingTerraformWorkingDir(tfws) // delete even if there are errors preparing the working dir
	if err != nil {
		if !strings.Contains(err.Error(), "reference not found") {
			return fmt.Errorf("failed to prepare working dir with GitRef %s: %w", ws.Spec.GitRef, err)
		}

		// If the branch was deleted, we should still be able to delete the workspace. This is especially true for CI workloads.
		goutil.Logger.Warnw("failed to prepare working dir with GitRef, trying main",
			"workspace", workspaceName,
			"operation", "delete",
			"error", err,
		)

		dir, err = util.PrepareTerraformWorkingDir(tfws, "workspace", "")
		if err != nil {
			return fmt.Errorf("failed to prepare working dir with the main GitRef: %w", err)
		}
	}

	err = terraform.ForceUnlockWorkspace(ctxBeforeTF, tfws)
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
		"REGION="+cl.Spec.Region,
		"TF_WORKSPACE="+tfws,
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

	ctxAfterTFApply, cancelAfterTFApply := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancelAfterTFApply()

	cl, err = cluster.DataStore.Get(ctxAfterTFApply, ws.Spec.ClusterName)
	if err != nil {
		goutil.Logger.Errorw("failed to get cluster",
			"cluster", ws.Spec.ClusterName,
			"operation", "delete",
			"error", err,
		)
	} else {
		cl.Status.Workspaces = goutil.RemoveString(cl.Status.Workspaces, workspaceName)
		// TODO: data race: if two goroutines are concurrently updating the cluster, this will fail.
		if err := cluster.DataStore.UpdateStatus(context.Background(), cl.Name, cl); err != nil {
			goutil.Logger.Errorw("failed to remove the deleted workspace from cluster",
				"workspace", workspaceName,
				"cluster", cl.Name,
				"operation", "delete",
				"error", err,
			)
		}
	}

	err = terraform.DeleteEmptyWorkspace(ctxAfterTFApply, tfws)
	if err != nil {
		return fmt.Errorf("failed to delete terraform workspace: %w", err)
	}
	goutil.Logger.Infow("deleted terraform workspace",
		"TerraformWorkspace", workspaceName,
		"operation", "delete",
	)

	goutil.Logger.Infow("deleted workspace",
		"workspace", workspaceName,
		"operation", "delete",
	)

	return nil
}

func List(ctx context.Context) ([]*crdv1alpha1.LeptonWorkspace, error) {
	wss, err := DataStore.List(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to list workspaces: %w", err)
	}
	return wss, nil
}

func Get(ctx context.Context, workspaceName string) (*crdv1alpha1.LeptonWorkspace, error) {
	return DataStore.Get(ctx, workspaceName)
}

func idempotentCreate(ctx context.Context, ws *crdv1alpha1.LeptonWorkspace) (*crdv1alpha1.LeptonWorkspace, error) {
	goutil.Logger.Infow("creating workspace",
		"workspace", ws.Spec.Name,
		"operation", "create",
	)

	var err error
	workspaceName := ws.Spec.Name

	err = terraform.CreateWorkspace(ctx, terraformWorkspaceName(workspaceName))
	if err != nil {
		if !strings.Contains(err.Error(), "already exists") && !strings.Contains(err.Error(), "already been taken") {
			return nil, fmt.Errorf("failed to create terraform workspace: %w", err)
		} else {
			goutil.Logger.Infow("terraform workspace already exists",
				"TerraformWorkspace", workspaceName,
				"operation", "create",
			)
		}
	} else {
		goutil.Logger.Infow("created terraform workspace",
			"TerraformWorkspace", workspaceName,
			"operation", "create",
		)
	}

	err = Worker.CreateJob(30*time.Minute, workspaceName, func(logCh chan<- string) error {
		cerr := createOrUpdateWorkspace(metrics.NewCtxWithJobKind("create"), ws, logCh)
		if cerr != nil {
			goutil.Logger.Errorw("failed to create or update workspace",
				"workspace", workspaceName,
				"operation", "create",
				"error", cerr,
			)
		} else {
			goutil.Logger.Infow("created workspace",
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

const DeploymentEnvironmentKey = "DEPLOYMENT_ENVIRONMENT"

func createOrUpdateWorkspace(ctx context.Context, ws *crdv1alpha1.LeptonWorkspace, logCh chan<- string) error {
	start := time.Now()
	jkind := metrics.ReadJobKindFromCtx(ctx)

	workspaceName := ws.Spec.Name
	var err error

	defer func() {
		metrics.ObserveClusterJobsLatency(jkind, err == nil, time.Since(start))

		if err == nil {
			ws.Status.LastState = ws.Status.State
			ws.Status.State = crdv1alpha1.WorkspaceOperationalStateReady
			metrics.IncrementWorkspaceJobsSuccessTotal(jkind)
		} else {
			metrics.IncrementWorkspaceJobsFailureTotal(jkind)
		}

		ws.Status.UpdatedAt = uint64(time.Now().Unix())
		derr := DataStore.UpdateStatus(context.Background(), workspaceName, ws)
		if err == nil && derr != nil {
			err = derr
		}
	}()

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	var cl *crdv1alpha1.LeptonCluster
	cl, err = cluster.DataStore.Get(ctx, ws.Spec.ClusterName)
	if err != nil {
		return fmt.Errorf("failed to get cluster: %w", err)
	}
	oidcID := cl.Status.Properties.OIDCID

	tfws := terraformWorkspaceName(workspaceName)
	dir, err := util.PrepareTerraformWorkingDir(tfws, "workspace", ws.Spec.GitRef)
	defer util.TryDeletingTerraformWorkingDir(tfws) // delete even if there are errors preparing the working dir
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	err = terraform.ForceUnlockWorkspace(ctx, tfws)
	if err != nil && !strings.Contains(err.Error(), "already unlocked") {
		return fmt.Errorf("failed to force unlock workspace: %w", err)
	}

	// derive deployment environment from the cluster
	dpEnv := cl.Spec.DeploymentEnvironment
	if dpEnv == "" {
		dpEnv = cluster.DeploymentEnvironmentValueTest
	}

	command := "sh"
	args := []string{"-c", "cd " + dir + " && ./install.sh"}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(),
		DeploymentEnvironmentKey+"="+dpEnv,
		"CLUSTER_NAME="+ws.Spec.ClusterName,
		"TF_API_TOKEN="+terraform.TempToken,
		"WORKSPACE_NAME="+workspaceName,
		"TF_WORKSPACE="+tfws,
		"REGION="+cl.Spec.Region,
		"IMAGE_TAG="+ws.Spec.ImageTag,
		"API_TOKEN="+ws.Spec.APIToken,
		"OIDC_ID="+oidcID,
		"WEB_ENABLED="+strconv.FormatBool(ws.Spec.EnableWeb),
		"CREATE_EFS=true",
		"VPC_ID="+cl.Status.Properties.VPCID,
		"EFS_MOUNT_TARGETS="+efsMountTargets(cl.Status.Properties.VPCPublicSubnets),
		"STATE="+string(ws.Spec.State),
	)
	if ws.Spec.QuotaGroup == "unlimited" {
		cmd.Env = append(cmd.Env,
			"ENABLE_QUOTA=false",
		)
	} else {
		cmd.Env = append(cmd.Env,
			"ENABLE_QUOTA=true",
			"QUOTA_CPU="+fmt.Sprint(ws.Spec.QuotaCPU),
			"QUOTA_MEMORY="+fmt.Sprint(ws.Spec.QuotaMemoryInGi),
			"QUOTA_GPU="+fmt.Sprint(ws.Spec.QuotaGPU),
		)
	}
	if CertificateARN != "" {
		// e.g.,
		// if “arn:aws:acm:us-east-1:605454121064:certificate/d8d5e0e1-ecc5-4716-aa79-01625e60704d”
		// then only take the last element (d8d5e0e1-ecc5-4716-aa79-01625e60704d)
		arnComponents := strings.Split(CertificateARN, "/")
		cmd.Env = append(cmd.Env, "TLS_CERT_ARN_ID="+arnComponents[len(arnComponents)-1])
	}
	if RootDomain != "" {
		cmd.Env = append(cmd.Env, "ROOT_DOMAIN="+RootDomain)
	}
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

func terraformWorkspaceName(workspaceName string) string {
	domain := strings.Split(RootDomain, ".")[0]
	return "ws-" + workspaceName + "-" + domain
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
		goutil.Logger.Errorw("failed to get workspace",
			"workspace", workspaceName,
			"error", err,
		)
		return
	}
	if err := updateState(ws, crdv1alpha1.WorkspaceOperationalStateFailed); err != nil {
		goutil.Logger.Errorw("failed to update workspace state to failed",
			"workspace", workspaceName,
			"error", err,
		)
	}
}

func updateState(ws *crdv1alpha1.LeptonWorkspace, state crdv1alpha1.LeptonWorkspaceOperationalState) error {
	ws.Status.LastState = ws.Status.State
	ws.Status.State = state
	ws.Status.UpdatedAt = uint64(time.Now().Unix())
	return DataStore.UpdateStatus(context.Background(), ws.Spec.Name, ws)
}

const (
	SysOverheadCPU        = 1
	SysOverheadMemoryInGi = 1
	SysOverheadGPU        = 0
)

func generateQuotaFromQuotaGroup(spec *crdv1alpha1.LeptonWorkspaceSpec) error {
	switch spec.QuotaGroup {
	case "small":
		spec.QuotaCPU = 16
		spec.QuotaMemoryInGi = 64
		spec.QuotaGPU = 1
	case "medium":
		spec.QuotaCPU = 64
		spec.QuotaMemoryInGi = 256
		spec.QuotaGPU = 4
	case "large":
		spec.QuotaCPU = 256
		spec.QuotaMemoryInGi = 1024
		spec.QuotaGPU = 16
	case "unlimited":
		spec.QuotaCPU = 0
		spec.QuotaMemoryInGi = 0
		spec.QuotaGPU = 0
	case "custom":
	default:
		return fmt.Errorf("invalid quota group %s", spec.QuotaGroup)
	}
	if spec.QuotaGroup != "unlimited" {
		spec.QuotaCPU += SysOverheadCPU
		spec.QuotaMemoryInGi += SysOverheadMemoryInGi
		spec.QuotaGPU += SysOverheadGPU
	}
	return nil
}
