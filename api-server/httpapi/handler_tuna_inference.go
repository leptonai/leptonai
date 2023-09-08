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
	"time"

	"github.com/leptonai/lepton/api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/k8s/leptonlabels"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/utils/ptr"

	"github.com/gin-gonic/gin"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
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

	State leptonaiv1alpha1.LeptonDeploymentState `json:"state"`
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

func (ih *InferenceHandler) AddToRoute(r gin.IRoutes) {
	r.GET("/tuna/inference", ih.List)
	r.POST("/tuna/inference", ih.Create)
	r.GET("/tuna/inference/:tiname", ih.Get)
	r.DELETE("/tuna/inference/:tiname", ih.Delete)
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
		name := ti.Metadata.Name
		ti.Metadata.Name = ih.workspaceName + "-" + name
		r := c.Request.Clone(c)

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

		err = createDummyDeployment(name, ih.namespace)
		if err != nil {
			goutil.Logger.Errorw("failed to create dummy deployment for billing",
				"operation", "createTunaInference",
				"deployment", name,
				"error", err,
			)
			return
		}

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
	ti.Status.State = ctrl.Status.State

	c.JSON(http.StatusOK, ti)
}

// Delete deletes a tuna inference deployment
func (ih *InferenceHandler) Delete(c *gin.Context) {
	name := c.Param("tiname")

	if !ih.isSysWorkspace {
		ih.forwardToSysWorkspace(c)

		err := deleteDummyDeployment(name, ih.namespace)
		if err != nil && !apierrors.IsNotFound(err) {
			goutil.Logger.Errorw("failed to delete dummy deployment for billing",
				"operation", "deleteTunaInference",
				"deployment", name,
				"error", err,
			)
		}

		return
	}

	ih.deleteDeployment(c, tunaDeploymentName(name))
}

func (ih *InferenceHandler) createTunaDeployment(c *gin.Context, ti TunaInference) error {
	mountPath := "/mnt/model"

	userSpec := leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	userSpec.PhotonID = ti.Spec.PhotonID
	userSpec.Name = tunaDeploymentName(ti.Metadata.Name)
	userSpec.ResourceRequirement.ResourceShape = leptonaiv1alpha1.AC1A10
	userSpec.ResourceRequirement.MinReplicas = ptr.To[int32](1)

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
	r := c.Request.Clone(c)
	r.URL.Path = strings.Replace(r.URL.Path, "/tuna/inference/", "/tuna/inference/"+ih.workspaceName+"-", 1)
	ih.sysProxy.ServeHTTP(c.Writer, r)
}

// create a dummy deployment in this namespace for billing purpose
func createDummyDeployment(name, namespace string) error {
	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "tuna-dummy-" + name,
			Namespace: namespace,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: ptr.To[int32](1),
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"app.kubernetes.io/name":                             "tuna-dummy-" + name,
					leptonlabels.LabelKeyLeptonDeploymentNameDepreciated: "tuna-dummy-" + name,
					leptonlabels.LabelKeyLeptonDeploymentName:            "tuna-dummy-" + name,
				},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app.kubernetes.io/name":                              "tuna-dummy-" + name,
						leptonlabels.LabelKeyLeptonDeploymentShapeDepreciated: string(leptonaiv1alpha1.TunaMedium),
						leptonlabels.LabelKeyLeptonDeploymentShape:            string(leptonaiv1alpha1.TunaMedium),
						leptonlabels.LabelKeyLeptonDeploymentNameDepreciated:  "tuna-dummy-" + name,
						leptonlabels.LabelKeyLeptonDeploymentName:             "tuna-dummy-" + name,
					},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:    "sleep-container",
							Image:   "alpine",
							Command: []string{"sleep", "infinity"},
							Resources: corev1.ResourceRequirements{
								Requests: corev1.ResourceList{
									corev1.ResourceCPU:    resource.MustParse("0"),
									corev1.ResourceMemory: resource.MustParse("0"),
								},
							},
						},
					},
				},
			},
		},
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	return k8s.MustLoadDefaultClient().Create(ctx, deployment)
}

func deleteDummyDeployment(name, namespace string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	return k8s.MustLoadDefaultClient().Delete(ctx, &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "tuna-dummy-" + name,
			Namespace: namespace,
		},
	})
}
