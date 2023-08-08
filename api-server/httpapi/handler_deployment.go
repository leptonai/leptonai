package httpapi

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/leptonai/lepton/api-server/quota"
	"github.com/leptonai/lepton/api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"github.com/gin-gonic/gin"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

type DeploymentHandler struct {
	Handler
}

func (h *DeploymentHandler) Create(c *gin.Context) {
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		goutil.Logger.Warnw("failed to read request body",
			"operation", "createDeployment",
			"error", err,
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to read request body: " + err.Error()})
		return
	}

	userSpec := leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	if err := json.Unmarshal(body, &userSpec); err != nil {
		goutil.Logger.Debugw("failed to unmarshal request body",
			"operation", "createDeployment",
			"error", err,
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "malformed deployment spec: " + err.Error()})
		return
	}

	ld, err := h.createFromUserSpec(c, userSpec)
	if err != nil {
		return
	}

	goutil.Logger.Infow("created deployment",
		"deployment", userSpec.Name,
		"operation", "createDeployment",
	)
	c.JSON(http.StatusCreated, NewLeptonDeployment(ld).Output())
}

func (h *DeploymentHandler) createFromUserSpec(c *gin.Context, spec leptonaiv1alpha1.LeptonDeploymentUserSpec) (*leptonaiv1alpha1.LeptonDeployment, error) {
	if err := h.validateCreateInput(c, &spec); err != nil {
		goutil.Logger.Debugw("invalid input",
			"operation", "createDeployment",
			"error", err,
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeValidationError, "message": "invalid deployment spec: " + err.Error()})
		return nil, err
	}

	ld := &leptonaiv1alpha1.LeptonDeployment{}
	ld.Spec.LeptonDeploymentUserSpec = spec

	ph, err := h.phDB.Get(c, ld.Spec.PhotonID)
	if apierrors.IsNotFound(err) {
		goutil.Logger.Debugw("photon not found",
			"deployment", spec.Name,
			"photon", ld.Spec.PhotonID,
			"operation", "createDeployment",
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "invalid deployemnt spec: photon " + ld.Spec.PhotonID + " does not exist."})
		return nil, err
	}
	if err != nil {
		goutil.Logger.Errorw("failed to get photon",
			"deployment", spec.Name,
			"photon", ld.Spec.PhotonID,
			"operation", "createDeployment",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get photon " + ld.Spec.PhotonID + ": " + err.Error()})
		return nil, err
	}

	// efsID:path:accessPointID
	efsFields := strings.Split(h.efsID, ":")
	efsID := efsFields[0]
	efsAccessPointID := ""
	if len(efsFields) >= 3 {
		efsAccessPointID = efsFields[2]
	}
	ld.Spec.LeptonDeploymentSystemSpec = leptonaiv1alpha1.LeptonDeploymentSystemSpec{
		PhotonName:                    ph.GetSpecName(),
		PhotonImage:                   util.UpdateDefaultRegistry(ph.Spec.Image, h.photonImageRegistry),
		BucketName:                    h.bucketName,
		EFSID:                         efsID,
		EFSAccessPointID:              efsAccessPointID,
		PhotonPrefix:                  h.photonPrefix,
		S3ReadOnlyAccessK8sSecretName: h.s3ReadOnlyAccessK8sSecretName,
		RootDomain:                    h.rootDomain,
		WorkspaceName:                 h.workspaceName,
		CertificateARN:                h.certARN,
	}
	ld.Spec.WorkspaceToken = h.apiToken
	ld.Namespace = h.namespace
	ld.Name = ld.GetSpecName()

	err = h.ldDB.Create(c, ld.Name, ld)
	if apierrors.IsAlreadyExists(err) {
		goutil.Logger.Debugw("deployment already exists",
			"deployment", spec.Name,
			"operation", "createDeployment",
		)
		c.JSON(http.StatusConflict, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "deployment " + ld.Name + " already exists"})
		return nil, err
	}
	if err != nil {
		goutil.Logger.Errorw("failed to create deployment",
			"deployment", spec.Name,
			"operation", "create",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create deployment: " + err.Error()})
		return nil, err
	}

	ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateStarting

	return ld, nil
}

func (h *DeploymentHandler) List(c *gin.Context) {
	lds, err := h.ldDB.List(c)
	if err != nil {
		goutil.Logger.Errorw("failed to list deployments",
			"operation", "listDeployments",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list deployments: " + err.Error()})
		return
	}
	ret := make([]*LeptonDeployment, 0, len(lds))
	for _, ld := range lds {
		ret = append(ret, NewLeptonDeployment(ld).Output())
	}

	c.JSON(http.StatusOK, ret)
}

func (h *DeploymentHandler) Update(c *gin.Context) {
	did := c.Param("did")
	ld, err := h.ldDB.Get(c, did)
	if apierrors.IsNotFound(err) {
		goutil.Logger.Debugw("deployment not found",
			"deployment", did,
			"operation", "updateDeployment",
		)
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + did + " not found"})
		return
	}
	if err != nil {
		goutil.Logger.Errorw("failed to get deployment",
			"deployment", did,
			"operation", "updateDeployment",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get deployment " + did + ": " + err.Error()})
		return
	}

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		goutil.Logger.Warnw("failed to read request body",
			"deployment", did,
			"operation", "updateDeployment",
			"error", err,
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to read request body: " + err.Error()})
		return
	}

	spec := &leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	if err := json.Unmarshal(body, &spec); err != nil {
		goutil.Logger.Debugw("failed to unmarshal deployment spec",
			"deployment", did,
			"operation", "updateDeployment",
			"error", err,
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "malformed deployment spec: " + err.Error()})
		return
	}
	spec.Name = did

	if err := h.validateUpdateInput(c, ld, spec); err != nil {
		goutil.Logger.Debugw("invalid deployment spec",
			"deployment", did,
			"operation", "updateDeployment",
			"error", err,
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeValidationError, "message": "invalid deployment spec: " + err.Error()})
		return
	}

	var ph *leptonaiv1alpha1.Photon
	if spec.PhotonID != "" {
		ph, err = h.phDB.Get(c, spec.PhotonID)
		if apierrors.IsNotFound(err) {
			goutil.Logger.Debugw("photon not found",
				"deployment", did,
				"photon", spec.PhotonID,
				"operation", "updateDeployment",
			)
			c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "photon " + spec.PhotonID + " not found"})
			return
		}
		if err != nil {
			goutil.Logger.Errorw("failed to get photon",
				"deployment", did,
				"photon", spec.PhotonID,
				"operation", "updateDeployment",
				"error", err,
			)
			c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get photon " + spec.PhotonID + ": " + err.Error()})
			return
		}
	}

	if !h.patchDeployment(ld, ph, spec) {
		goutil.Logger.Debugw("no valid field to update",
			"deployment", did,
			"operation", "updateDeployment",
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeValidationError, "message": "no valid field to patch"})
		return
	}

	ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateUpdating

	err = h.ldDB.Update(c, ld.Name, ld)
	if apierrors.IsNotFound(err) {
		goutil.Logger.Errorw("deployment not found",
			"deployment", ld.GetSpecName(),
			"operation", "updateDeployment",
		)
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + ld.GetSpecName() + " not found"})
		return
	}
	if err != nil {
		goutil.Logger.Errorw("failed to update deployment",
			"deployment", ld.GetSpecName(),
			"operation", "updateDeployment",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to update deployment " + ld.GetSpecName() + ": " + err.Error()})
		return
	}

	goutil.Logger.Infow("updated deployment",
		"deployment", ld.GetSpecName(),
		"operation", "updateDeployment",
	)
	c.JSON(http.StatusOK, NewLeptonDeployment(ld).Output())
}

func (h *DeploymentHandler) Get(c *gin.Context) {
	did := c.Param("did")
	ld, err := h.ldDB.Get(c, did)
	if apierrors.IsNotFound(err) {
		goutil.Logger.Debugw("deployment not found",
			"deployment", did,
			"operation", "getDeployment",
		)
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + did + " not found"})
		return
	}
	if err != nil {
		goutil.Logger.Errorw("failed to get deployment",
			"deployment", did,
			"operation", "getDeployment",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get deployment " + did + ": " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, NewLeptonDeployment(ld).Output())
}

func (h *DeploymentHandler) Delete(c *gin.Context) {
	did := c.Param("did")
	h.deleteDeployment(c, did)
}

func (h *DeploymentHandler) deleteDeployment(c *gin.Context, name string) {
	err := h.ldDB.Delete(c, name)
	if apierrors.IsNotFound(err) {
		goutil.Logger.Debugw("requested to delete deployment that does not exist",
			"deployment", name,
			"operation", "deleteDeployment",
		)
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + name + " not found"})
		return
	}
	if err != nil {
		goutil.Logger.Errorw("failed to delete deployment",
			"deployment", name,
			"operation", "deleteDeployment",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete deployment " + name + ": " + err.Error()})
		return
	}

	goutil.Logger.Infow("successfully deleted deployment",
		"deployment", name,
		"operation", "deleteDeployment",
	)
	c.Status(http.StatusOK)
}

func (h *DeploymentHandler) validateCreateInput(ctx context.Context, ld *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
	if !util.ValidateName(ld.Name) {
		return fmt.Errorf("invalid name %s: %s", ld.Name, util.NameInvalidMessage)
	}
	if ld.ResourceRequirement.CPU < 0 {
		return fmt.Errorf("cpu must be non-negative")
	}
	if ld.ResourceRequirement.Memory < 0 {
		return fmt.Errorf("memory must be non-negative")
	}

	if ld.ResourceRequirement.ResourceShape != "" {
		if !(ld.ResourceRequirement.CPU == 0 && ld.ResourceRequirement.Memory == 0) {
			return fmt.Errorf("cpu and memory must be unspecified when resource shape is specified")
		}

		shape := leptonaiv1alpha1.DisplayShapeToShape(string(ld.ResourceRequirement.ResourceShape))

		if leptonaiv1alpha1.SupportedShapesAWS[shape] == nil {
			return fmt.Errorf("unsupported resource shape %s", ld.ResourceRequirement.ResourceShape)
		}
	} else {
		if ld.ResourceRequirement.CPU == 0 {
			return fmt.Errorf("cpu must be specified when resource shape is unspecified")
		}
		if ld.ResourceRequirement.Memory == 0 {
			return fmt.Errorf("memory must be specified when resource shape is unspecified")
		}
	}

	if ld.ResourceRequirement.MinReplicas <= 0 {
		return fmt.Errorf("min replicas must be positive")
	}

	err := h.checkQuota(ctx, ld, nil)
	if err != nil {
		return err
	}

	for _, env := range ld.Envs {
		if !goutil.ValidateEnvName(env.Name) {
			return fmt.Errorf(goutil.InvalidEnvNameMessage + ":" + env.Name)
		}
	}

	if h.phDB == nil { // for testing
		return nil
	}

	_, err = h.phDB.Get(ctx, ld.PhotonID)
	if apierrors.IsNotFound(err) {
		return fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}
	return err
}

// TODO: add test
func (h *DeploymentHandler) validateUpdateInput(ctx context.Context, old *leptonaiv1alpha1.LeptonDeployment, spec *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
	if spec.PhotonID != "" {
		ph, err := h.phDB.Get(ctx, spec.PhotonID)
		if apierrors.IsNotFound(err) {
			return fmt.Errorf("photon %s does not exist", spec.PhotonID)
		}
		if err != nil {
			return fmt.Errorf("failed to get photon %s: %s", spec.PhotonID, err)
		}
		if old.Spec.PhotonName != ph.GetSpecName() {
			return fmt.Errorf("can only update to a photon with the same name")
		}
	}

	err := h.checkQuota(ctx, spec, &old.Spec.LeptonDeploymentUserSpec)
	if err != nil {
		return err
	}

	return nil
}

func (h *DeploymentHandler) checkQuota(ctx context.Context, spec *leptonaiv1alpha1.LeptonDeploymentUserSpec, oldSpec *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
	if h.namespace == "" { // for testing
		goutil.Logger.Warnw("namespace not set, skip quota check",
			"operation", "check quota",
			"workspace", h.workspaceName,
		)
		return nil
	}

	q, err := k8s.GetResourceQuota(ctx, h.namespace, "quota-"+h.workspaceName)
	// if quota is not found, skip quota check since it is unlimited
	if apierrors.IsNotFound(err) {
		goutil.Logger.Warnw("resource quota not found",
			"operation", "check quota",
			"namespace", h.namespace,
			"workspace", h.workspaceName,
		)
		return nil
	}
	if err != nil {
		goutil.Logger.Errorw("failed to get resource quota",
			"operation", "check quota",
			"namespace", h.namespace,
			"workspace", h.workspaceName,
			"error", err,
		)
		return fmt.Errorf("failed to get resource quota: %v", err)
	}

	var cr *leptonaiv1alpha1.LeptonDeploymentResourceRequirement
	if oldSpec != nil {
		cr = &oldSpec.ResourceRequirement
	}

	if !quota.Admit(q, &spec.ResourceRequirement, cr) {
		return fmt.Errorf("resource requirement exceeds quota")
	}

	return nil
}

// Patch modifies the deployment with the given user spec.
func (h *DeploymentHandler) patchDeployment(old *leptonaiv1alpha1.LeptonDeployment, ph *leptonaiv1alpha1.Photon, spec *leptonaiv1alpha1.LeptonDeploymentUserSpec) bool {
	patched := false
	if spec.PhotonID != "" {
		old.Spec.PhotonID = spec.PhotonID
		old.Spec.PhotonImage = util.UpdateDefaultRegistry(ph.Spec.Image, h.photonImageRegistry)
		patched = true
	}
	if spec.ResourceRequirement.MinReplicas > 0 {
		old.Spec.ResourceRequirement.MinReplicas = spec.ResourceRequirement.MinReplicas
		patched = true
	}
	if spec.APITokens != nil {
		old.Spec.APITokens = spec.APITokens
		patched = true
	}
	if spec.Envs != nil {
		old.Spec.Envs = spec.Envs
		patched = true
	}
	if spec.Mounts != nil {
		old.Spec.Mounts = spec.Mounts
		patched = true
	}
	if spec.ResourceRequirement.ResourceShape != "" {
		old.Spec.ResourceRequirement.ResourceShape = spec.ResourceRequirement.ResourceShape
		patched = true
	}
	return patched
}
