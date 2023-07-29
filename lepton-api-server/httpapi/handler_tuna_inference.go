package httpapi

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

type TunaInference struct {
	Metadata Metadata `json:"metadata"`

	Spec   TunaInferenceSpec   `json:"spec"`
	Status TunaInferenceStatus `json:"status"`
}

type TunaInferenceSpec struct {
	PhotonID string `json:"photon_id"`

	TunaOutputDir string `json:"tuna_output_dir"`
}

type TunaInferenceStatus struct {
	ChatEndpoint string `json:"chat_endpoint"`
	APIEndpoint  string `json:"api_endpoint"`
}

type InferenceHandler struct {
	DeploymentHandler
	isSysWorkspace bool
	sysProxy       *httputil.ReverseProxy
}

func NewInferenceHandlerForSys(d DeploymentHandler) *InferenceHandler {
	return &InferenceHandler{
		DeploymentHandler: d,
		isSysWorkspace:    true,
	}
}

// NewInferenceHandler creates a new InferenceHandler
func NewInferenceHandler(d DeploymentHandler) *InferenceHandler {
	u := &url.URL{
		Scheme: "http",
		Host:   service.ServiceName("lepton-api-server") + "." + "ws-" + d.clusterName + "sys" + ".svc:20863",
	}
	sp := httputil.NewSingleHostReverseProxy(u)
	sp.ModifyResponse = func(resp *http.Response) error {
		// Have to remove CORS headers from response
		// The reverse proxy continues to merge headers even if we overwrite the modify response function here.
		// So we have to unset the CORS headers here instead of set it correctly.
		util.UnsetCORSForDashboard(resp.Header)
		return nil
	}

	return &InferenceHandler{
		DeploymentHandler: d,
		isSysWorkspace:    false,
		sysProxy:          sp,
	}
}

// Create creates a new tuna inference deployment
func (ih *InferenceHandler) Create(c *gin.Context) {
	ti := TunaInference{}
	err := c.BindJSON(&ti)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if !ih.isSysWorkspace {
		ti.Metadata.Name = ih.workspaceName + "-" + ti.Metadata.Name
		r := c.Request.Clone(context.Background())

		jti, err := json.Marshal(ti)
		if err != nil {
			goutil.Logger.Errorw("failed to marshal tuna inference",
				"operation", "createTunaInference",
				"deployment", ti.Metadata.Name,
				"error", err,
			)
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		r.Body = io.NopCloser(bytes.NewReader(jti))
		r.ContentLength = int64(len(jti))

		ih.sysProxy.ServeHTTP(c.Writer, r)
		return
	}

	err = ih.createTunaDeployment(c, ti)
	if err != nil {
		goutil.Logger.Errorw("failed to create tuna deployment",
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

// Get gets a tuna inference deployment
func (ih *InferenceHandler) Get(c *gin.Context) {
	if !ih.isSysWorkspace {
		ih.forwardToSysWorkspace(c)
		return
	}

	name := c.Param("tiname")
	ti := TunaInference{}
	ti.Metadata.Name = name

	ctrl, err := ih.ldDB.Get(c, tunaDeploymentName(name))
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "tuna deployment " + name + " not found"})
		return
	}
	ti.Spec.PhotonID = ctrl.Spec.LeptonDeploymentUserSpec.PhotonID
	ti.Status.ChatEndpoint = ctrl.Status.Endpoint.ExternalEndpoint + "/chat"
	ti.Status.APIEndpoint = ctrl.Status.Endpoint.ExternalEndpoint + "/api/v1"

	c.JSON(http.StatusOK, ti)
}

// Delete deletes a tuna inference deployment
func (ih *InferenceHandler) Delete(c *gin.Context) {
	if !ih.isSysWorkspace {
		ih.forwardToSysWorkspace(c)
		return
	}

	name := c.Param("tiname")
	err := ih.deleteFromName(c, tunaDeploymentName(name))
	if err != nil {
		goutil.Logger.Errorw("failed to delete tuna deployment",
			"operation", "deleteTunaDeployment",
			"deployment", name,
			"error", err,
		)
		return
	}

	c.Status(http.StatusOK)
}

func (ih *InferenceHandler) createTunaDeployment(c *gin.Context, ti TunaInference) error {
	mountPath := "/mnt/model"

	userSpec := leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	userSpec.PhotonID = ti.Spec.PhotonID
	userSpec.Name = tunaDeploymentName(ti.Metadata.Name)
	userSpec.ResourceRequirement.ResourceShape = leptonaiv1alpha1.AC1A10
	userSpec.ResourceRequirement.MinReplicas = 1

	userSpec.Envs = []leptonaiv1alpha1.EnvVar{
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

	_, err := ih.createFromUserSpec(c, userSpec)
	return err
}

func tunaDeploymentName(name string) string {
	return "tuna-" + name
}

func (ih *InferenceHandler) forwardToSysWorkspace(c *gin.Context) {
	r := c.Request.Clone(context.Background())
	r.URL.Path = strings.Replace(r.URL.Path, "/tuna/inference/", "/tuna/inference/"+ih.workspaceName+"-", 1)
	ih.sysProxy.ServeHTTP(c.Writer, r)
}
