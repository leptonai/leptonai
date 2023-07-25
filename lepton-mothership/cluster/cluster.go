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
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/go-pkg/worker"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
	"github.com/leptonai/lepton/lepton-mothership/util"

	"github.com/prometheus/client_golang/prometheus"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

var (
	RootDomain            string
	DeploymentEnvironment string
)

const (
	storeNamespace = "default"

	// NOTE: adjust based on per-account EKS quota
	maxClusters = 100
)

// Make cluster a struct and do not use global variables
// TODO: do we want to backup the cluster state?
var (
	DataStore = datastore.NewCRStore[*crdv1alpha1.LeptonCluster](
		storeNamespace,
		&crdv1alpha1.LeptonCluster{},
		nil,
	)

	Worker = worker.New()

	clusterTotal = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Namespace: "mothership",
			Subsystem: "cluster",
			Name:      "total",
			Help:      "Tracks the total number of clusters",
		},
	)

	failedAPIs = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "mothership",
			Subsystem: "cluster",
			Name:      "failed_apis",
			Help:      "Tracks failed mothership cluster operations",
		},
		[]string{"api"},
	)
)

func getTotalClusters(gatherer prometheus.Gatherer) int {
	gss, err := gatherer.Gather()
	if err != nil {
		log.Printf("failed to get default gatherer %v", err)
		return 0
	}
	for _, gs := range gss {
		if gs.GetName() == "mothership_cluster_total" && len(gs.Metric) > 0 {
			return int(*gs.Metric[0].GetGauge().Value)
		}
	}
	return 0
}

// Init initializes the cluster and retore any ongoing operations
func Init() {
	prometheus.MustRegister(
		clusterTotal,
		failedAPIs,
	)

	clusters, err := DataStore.List(context.Background())
	if err != nil {
		goutil.Logger.Fatalw("failed to list clusters",
			"error", err,
		)
		return
	}

	for _, item := range clusters {
		cl := item

		switch cl.Status.State {
		case crdv1alpha1.ClusterStateCreating, crdv1alpha1.ClusterStateUnknown:
			clusterTotal.Inc()
			go func() {
				goutil.Logger.Infow("restart creating cluster",
					"cluster", cl.Spec.Name,
					"operation", "create",
				)
				// call the idempotent create function
				_, err := idempotentCreate(cl)
				if err != nil {
					goutil.Logger.Errorw("failed to create cluster",
						"cluster", cl.Spec.Name,
						"operation", "create",
						"error", err,
					)
				}
			}()
		case crdv1alpha1.ClusterStateUpdating:
			clusterTotal.Inc()
			go func() {
				goutil.Logger.Infow("restart updating cluster",
					"cluster", cl.Spec.Name,
					"operation", "update",
				)
				_, err := Update(context.Background(), cl.Spec)
				if err != nil {
					goutil.Logger.Errorw("failed to update cluster",
						"cluster", cl.Spec.Name,
						"operation", "update",
						"error", err)
				}
			}()
		case crdv1alpha1.ClusterStateDeleting:
			clusterTotal.Inc()
			go func() {
				goutil.Logger.Infow("restart deleting cluster",
					"cluster", cl.Spec.Name,
					"operation", "delete",
				)
				err := Delete(cl.Spec.Name)
				if err != nil {
					goutil.Logger.Errorw("failed to delete cluster",
						"cluster", cl.Spec.Name,
						"operation", "delete",
						"error", err,
					)
				} else {
					clusterTotal.Dec()
				}
			}()
		}
	}
}

// Create schedules a cluster create job via "eks-lepton".
// Note that the cluster name is globally unique, guaranteed by the Kubernetes and namespace.
// A redundant cluster creation with the same name will fail.
func Create(ctx context.Context, spec crdv1alpha1.LeptonClusterSpec) (c *crdv1alpha1.LeptonCluster, err error) {
	clusterName := spec.Name
	if !util.ValidateName(clusterName) {
		return nil, fmt.Errorf("invalid cluster name %s: %s", clusterName, util.NameInvalidMessage)
	}

	totalClusters := getTotalClusters(prometheus.DefaultGatherer)
	log.Printf("currently total %d clusters... creating one more", totalClusters)
	if totalClusters >= maxClusters {
		return nil, fmt.Errorf("max cluster size limit exceeded (up to %d)", maxClusters)
	}

	defer func() {
		if err == nil {
			clusterTotal.Inc()
		}
	}()

	cl := &crdv1alpha1.LeptonCluster{
		Spec: spec,
	}
	if cl.Spec.DeploymentEnvironment == "" {
		cl.Spec.DeploymentEnvironment = DeploymentEnvironment
	}
	if err := DataStore.Create(ctx, clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to create cluster: %w", err)
	}
	cl.Status = crdv1alpha1.LeptonClusterStatus{
		LastState: crdv1alpha1.ClusterStateUnknown,
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
		return nil, fmt.Errorf("invalid cluster name %s: %s", clusterName, util.NameInvalidMessage)
	}

	cl, err := DataStore.Get(ctx, clusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get cluster: %w", err)
	}

	if cl.Status.State != crdv1alpha1.ClusterStateReady {
		goutil.Logger.Warnw("updating a non-ready cluster",
			"cluster", clusterName,
			"operation", "update",
		)
	}

	// only allow updating certain fields
	if spec.GitRef != "" {
		cl.Spec.GitRef = spec.GitRef
	}

	if err := DataStore.Update(ctx, clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster: %w", err)
	}
	cl.Status.LastState = cl.Status.State
	cl.Status.State = crdv1alpha1.ClusterStateUpdating
	cl.Status.UpdatedAt = uint64(time.Now().Unix())
	if err := DataStore.UpdateStatus(ctx, clusterName, cl); err != nil {
		return nil, fmt.Errorf("failed to update cluster status: %w", err)
	}

	err = Worker.CreateJob(120*time.Minute, clusterName, func(logCh chan<- string) error {
		cerr := createOrUpdateCluster(context.Background(), cl, logCh)
		if cerr != nil {
			goutil.Logger.Errorw("failed to update cluster",
				"cluster", clusterName,
				"operation", "update",
				"error", cerr,
			)
		}
		return cerr
	}, func() {
		tryUpdatingStateToFailed(context.Background(), clusterName)
		failedAPIs.WithLabelValues("create").Inc()
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create job: %w", err)
	}

	return cl, nil
}

func Delete(clusterName string) error {
	return Worker.CreateJob(120*time.Minute, clusterName, func(logCh chan<- string) error {
		return delete(clusterName, logCh)
	}, func() {
		tryUpdatingStateToFailed(context.Background(), clusterName)
		failedAPIs.WithLabelValues("delete").Inc()
	})
}

func delete(clusterName string, logCh chan<- string) error {
	cl, err := DataStore.Get(context.Background(), clusterName)
	if err != nil {
		if apierrors.IsNotFound(err) {
			goutil.Logger.Infow("cluster not found",
				"cluster", clusterName,
				"operation", "delete",
			)

			return fmt.Errorf("cluster %q not found", clusterName)
		}

		return fmt.Errorf("failed to get cluster: %w", err)
	}

	cl.Status.LastState = cl.Status.State
	cl.Status.State = crdv1alpha1.ClusterStateDeleting
	if err := DataStore.UpdateStatus(context.Background(), clusterName, cl); err != nil {
		return fmt.Errorf("failed to update cluster status: %w", err)
	}

	defer func() {
		success := err == nil
		if err == nil {
			if err = DataStore.Delete(context.Background(), clusterName); err != nil {
				goutil.Logger.Errorw("failed to delete cluster from the data store",
					"cluster", clusterName,
					"operation", "delete",
					"error", err,
				)

				success = false
			}
		}
		if success {
			goutil.Logger.Infow("successfully deleted cluster",
				"cluster", clusterName,
				"operation", "delete",
			)
			return
		}
		goutil.Logger.Errorw("failed to delete cluster",
			"cluster", clusterName,
			"operation", "delete",
			"error", err,
		)

		// TODO: implement fallback in case tf destroy fails

		// we are NOT going to rely on thie fallback
		// we should fix the terraform/provisioner destory
		// this is only used as fallback to minimize the aws bill
		//
		// clean up logic:
		// step 1. inspect the cluster based on provider resources
		// step 2. query all related cloud resources based on cluster info + tagging
		// step 3. manually delete resources
		//
		// step 4 (optional):
		// manually issue mothership delete API with force option
		// to delete mothership(k8s) resources
		//
		// do not try to delete everything such as mothership resources
		// as long as we destroy AWS-bill generating resources with best effort
		// we should debug why the delete failed manually and actually fix the root cause
	}()

	tfws := terraformWorkspaceName(clusterName)
	_, err = terraform.GetWorkspace(tfws)
	if err != nil {
		// TODO: check if workspace does not exist. If it does not exist, then it is already deleted.
		return fmt.Errorf("failed to get workspace: %w", err)
	}

	err = terraform.ForceUnlockWorkspace(tfws)
	if err != nil && !strings.Contains(err.Error(), "already unlocked") {
		return fmt.Errorf("failed to force unlock workspace: %w", err)
	}

	dir, err := util.PrepareTerraformWorkingDir(tfws, "eks-lepton", cl.Spec.GitRef)
	defer util.TryDeletingTerraformWorkingDir(tfws) // delete even if there are errors preparing the working dir
	if err != nil {
		if !strings.Contains(err.Error(), "reference not found") {
			return fmt.Errorf("failed to prepare working dir with GitRef %s: %w", cl.Spec.GitRef, err)
		}

		// If the branch was deleted, we should still be able to delete the cluster.
		// This is especially true when we were testing
		goutil.Logger.Warnw("failed to prepare working dir with GitRef, trying main",
			"cluster", clusterName,
			"operation", "delete",
			"error", err,
		)

		dir, err = util.PrepareTerraformWorkingDir(tfws, "eks-lepton", "")
		if err != nil {
			return fmt.Errorf("failed to prepare working dir with the main GitRef: %w", err)
		}
	}

	dpEnv := cl.Spec.DeploymentEnvironment

	command := "sh"
	args := []string{"-c", "cd " + dir + " && ./uninstall.sh"}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(),
		DeploymentEnvironmentKey+"="+dpEnv,
		"REGION="+cl.Spec.Region,
		"CLUSTER_NAME="+clusterName,
		"TF_WORKSPACE="+tfws,
		"TF_API_TOKEN="+terraform.TempToken,
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

	err = terraform.DeleteEmptyWorkspace(terraformWorkspaceName(clusterName))
	if err != nil {
		return fmt.Errorf("failed to delete terraform workspace: %w", err)
	}
	goutil.Logger.Infow("deleted terraform workspace",
		"cluster", clusterName,
		"operation", "delete",
	)
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
	return DataStore.Get(ctx, clusterName)
}

func idempotentCreate(cl *crdv1alpha1.LeptonCluster) (*crdv1alpha1.LeptonCluster, error) {
	var err error
	clusterName := cl.Spec.Name

	err = terraform.CreateWorkspace(terraformWorkspaceName(clusterName))
	if err != nil {
		if !strings.Contains(err.Error(), "already exists") && !strings.Contains(err.Error(), "already been taken") {
			return nil, fmt.Errorf("failed to create terraform workspace: %w", err)
		} else {
			goutil.Logger.Infow("skip terraform workspace creation: already exists",
				"cluster", clusterName,
				"TerraformWorkspace", clusterName,
				"operation", "create",
			)
		}
	} else {
		goutil.Logger.Infow("created terraform workspace",
			"cluster", clusterName,
			"TerraformWorkspace", clusterName,
			"operation", "create",
		)
	}

	err = terraform.ForceUnlockWorkspace(terraformWorkspaceName(clusterName))
	if err != nil && !strings.Contains(err.Error(), "already unlocked") {
		return nil, fmt.Errorf("failed to force unlock workspace: %w", err)
	}

	err = Worker.CreateJob(120*time.Minute, clusterName, func(logCh chan<- string) error {
		cerr := createOrUpdateCluster(context.Background(), cl, logCh)
		if cerr != nil {
			goutil.Logger.Errorw("failed to create cluster",
				"cluster", clusterName,
				"operation", "create",
				"error", cerr,
			)
		}
		return cerr
	}, func() {
		tryUpdatingStateToFailed(context.Background(), clusterName)
		failedAPIs.WithLabelValues("update").Inc()
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create job: %w", err)
	}

	return cl, nil
}

const (
	DeploymentEnvironmentKey       = "DEPLOYMENT_ENVIRONMENT"
	DeploymentEnvironmentValueTest = "TEST"
	DeploymentEnvironmentValueDev  = "DEV"
	DeploymentEnvironmentValueProd = "PROD"
)

func createOrUpdateCluster(ctx context.Context, cl *crdv1alpha1.LeptonCluster, logCh chan<- string) error {
	clusterName := cl.Spec.Name
	var err error

	defer func() {
		if err == nil {
			// if err != nil, the state will be updated in the failure handler
			cl.Status.LastState = cl.Status.State
			cl.Status.State = crdv1alpha1.ClusterStateReady
		}
		cl.Status.UpdatedAt = uint64(time.Now().Unix())
		derr := DataStore.UpdateStatus(ctx, clusterName, cl)
		if err == nil && derr != nil {
			err = derr
		}
	}()

	tfws := terraformWorkspaceName(clusterName)
	dir, err := util.PrepareTerraformWorkingDir(tfws, "eks-lepton", cl.Spec.GitRef)
	defer util.TryDeletingTerraformWorkingDir(tfws) // delete even if there are errors preparing the working dir
	if err != nil {
		return fmt.Errorf("failed to prepare working dir: %w", err)
	}

	dpEnv := cl.Spec.DeploymentEnvironment

	command := "sh"
	args := []string{"-c", "cd " + dir + " && ./install.sh"}

	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(),
		DeploymentEnvironmentKey+"="+dpEnv,
		"REGION="+cl.Spec.Region,
		"CLUSTER_NAME="+clusterName,
		"TF_WORKSPACE="+tfws,
		"TF_API_TOKEN="+terraform.TempToken)
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
	cmd.Env = append(os.Environ(),
		"CLUSTER_NAME="+clusterName,
		"TF_WORKSPACE="+tfws,
		"TF_API_TOKEN="+terraform.TempToken,
	)
	var output []byte
	output, err = cmd.CombinedOutput()
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

func terraformWorkspaceName(clusterName string) string {
	domain := strings.Split(RootDomain, ".")[0]
	return "cl-" + clusterName + "-" + domain
}

func tryUpdatingStateToFailed(ctx context.Context, clusterName string) {
	cl, err := DataStore.Get(ctx, clusterName)
	if err != nil {
		goutil.Logger.Errorw("failed to get cluster",
			"cluster", clusterName,
			"operation", "update cluster state",
			"error", err,
		)
		return
	}

	if err := updateState(ctx, cl, crdv1alpha1.ClusterStateFailed); err != nil {
		goutil.Logger.Errorw("failed to update the cluster",
			"cluster", clusterName,
			"operation", "update cluster state",
			"error", err,
		)
	}
}

func updateState(ctx context.Context, cl *crdv1alpha1.LeptonCluster, state crdv1alpha1.LeptonClusterState) error {
	cl.Status.LastState = cl.Status.State
	cl.Status.State = state
	cl.Status.UpdatedAt = uint64(time.Now().Unix())
	return DataStore.UpdateStatus(ctx, cl.Spec.Name, cl)
}
