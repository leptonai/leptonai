package httpapi

import (
	"context"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

type TunaInference struct {
	Metadata Metadata            `json:"metadata"`
	Spec     TunaInferenceSpec   `json:"spec"`
	Status   TunaInferenceStatus `json:"status"`
}

type TunaInferenceSpec struct {
	TunaOutputDir string `json:"tuna_output_dir"`

	ControllerPhotonID string `json:"controller_photon_id"`
	WorkerPhotonID     string `json:"worker_photon_id"`
	FrontendPhotonID   string `json:"frontend_photon_id"`
}

type TunaInferenceStatus struct {
	FrontendEndpoint string `json:"frontend_endpoint"`
}

type InferenceHandler struct {
	DeploymentHandler
}

func NewInferenceHandler(d DeploymentHandler) *InferenceHandler {
	return &InferenceHandler{
		DeploymentHandler: d,
	}
}

func (ih *InferenceHandler) Create(c *gin.Context) {
	ti := TunaInference{}
	err := c.BindJSON(&ti)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	err = ih.createControllerDeployment(c, ti)
	if err != nil {
		goutil.Logger.Errorw("failed to create controller deployment",
			"operation", "createTunaInference",
			"deployment", ti.Metadata.Name,
			"error", err,
		)
		return
	}

	err = ih.createWorkerDeployment(c, ti)
	if err != nil {
		goutil.Logger.Errorw("failed to create worker deployment",
			"operation", "createTunaInference",
			"deployment", ti.Metadata.Name,
			"error", err,
		)
		return
	}

	err = ih.createFrontendDeployment(c, ti)
	if err != nil {
		goutil.Logger.Errorw("failed to create frontend deployment",
			"operation", "createTunaInference",
			"deployment", ti.Metadata.Name,
			"error", err,
		)
		return
	}

	goutil.Logger.Infow("created tuna inference",
		"operation", "createTunaInference",
		"deployment", ti.Metadata.Name,
	)

	c.Status(http.StatusCreated)
}

func (ih *InferenceHandler) Get(c *gin.Context) {
	name := c.Param("tiname")

	ti := TunaInference{}
	ti.Metadata.Name = name

	ctrl, err := ih.ldDB.Get(context.Background(), controllerName(name))
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "controller deployment " + name + " not found"})
		return
	}
	ti.Spec.ControllerPhotonID = ctrl.Spec.LeptonDeploymentUserSpec.PhotonID

	worker, err := ih.ldDB.Get(context.Background(), workerName(name))
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "worker deployment " + name + " not found"})
		return
	}
	ti.Spec.WorkerPhotonID = worker.Spec.LeptonDeploymentUserSpec.PhotonID

	frontend, err := ih.ldDB.Get(context.Background(), frontendName(name))
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "frontend deployment " + name + " not found"})
		return
	}
	ti.Spec.FrontendPhotonID = frontend.Spec.LeptonDeploymentUserSpec.PhotonID

	ti.Status.FrontendEndpoint = frontend.Status.Endpoint.ExternalEndpoint

	c.JSON(http.StatusOK, ti)
}

func (ih *InferenceHandler) Delete(c *gin.Context) {
	name := c.Param("tiname")
	err := ih.deleteFromName(c, controllerName(name))
	if err != nil {
		goutil.Logger.Errorw("failed to delete controller deployment",
			"operation", "deleteControllerDeployment",
			"deployment", name,
			"error", err,
		)
		return
	}

	err = ih.deleteFromName(c, workerName(name))
	if err != nil {
		goutil.Logger.Errorw("failed to delete worker deployment",
			"operation", "deleteWorkerDeployment",
			"deployment", name,
			"error", err,
		)
		return
	}

	err = ih.deleteFromName(c, frontendName(name))
	if err != nil {
		goutil.Logger.Errorw("failed to delete frontend deployment",
			"operation", "deleteFrontendDeployment",
			"deployment", name,
			"error", err,
		)
		return
	}

	c.Status(http.StatusOK)
}

func (ih *InferenceHandler) createControllerDeployment(c *gin.Context, ti TunaInference) error {
	userSpec := leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	userSpec.PhotonID = ti.Spec.ControllerPhotonID
	userSpec.Name = controllerName(ti.Metadata.Name)
	userSpec.ResourceRequirement.ResourceShape = leptonaiv1alpha1.GP1Small
	userSpec.ResourceRequirement.MinReplicas = 1

	_, err := ih.createFromUserSpec(c, userSpec)
	return err
}

func (ih *InferenceHandler) createWorkerDeployment(c *gin.Context, ti TunaInference) error {
	mountPath := "/mnt/model"

	userSpec := leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	userSpec.PhotonID = ti.Spec.WorkerPhotonID
	userSpec.Name = workerName(ti.Metadata.Name)
	userSpec.Envs = []leptonaiv1alpha1.EnvVar{
		{
			Name:  "CONTROLLER_ADDR",
			Value: getSVCAddress(controllerName(ti.Metadata.Name), ih.namespace),
		},
		{
			Name:  "WORKER_ADDR",
			Value: getSVCAddress(workerName(ti.Metadata.Name), ih.namespace),
		},
		{
			Name:  "MODEL_PATH",
			Value: mountPath,
		},
	}
	userSpec.Mounts = []leptonaiv1alpha1.Mount{
		{
			Path:      ti.Spec.TunaOutputDir,
			MountPath: mountPath,
		},
	}
	userSpec.ResourceRequirement.ResourceShape = leptonaiv1alpha1.AC1A10
	userSpec.ResourceRequirement.MinReplicas = 1

	_, err := ih.createFromUserSpec(c, userSpec)
	return err
}

func (ih *InferenceHandler) createFrontendDeployment(c *gin.Context, ti TunaInference) error {
	userSpec := leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	userSpec.PhotonID = ti.Spec.FrontendPhotonID
	userSpec.Name = frontendName(ti.Metadata.Name)
	userSpec.ResourceRequirement.ResourceShape = leptonaiv1alpha1.GP1Small
	userSpec.ResourceRequirement.MinReplicas = 1
	userSpec.Envs = []leptonaiv1alpha1.EnvVar{
		{
			Name:  "CONTROLLER_ADDR",
			Value: getSVCAddress(controllerName(ti.Metadata.Name), ih.namespace),
		},
	}

	_, err := ih.createFromUserSpec(c, userSpec)
	return err
}

func getSVCAddress(name string, namespace string) string {
	return "http://" + service.ServiceName(name) + "." + namespace + ".svc:8080"
}

func controllerName(name string) string {
	return name + "-ctrl"
}

func workerName(name string) string {
	return name + "-worker"
}

func frontendName(name string) string {
	return name + "-frontend"
}
