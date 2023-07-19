package httpapi

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

type DeploymentHandler struct {
	Handler
}

func (h *DeploymentHandler) Create(c *gin.Context) {
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to read request body: " + err.Error()})
		return
	}

	ld := &leptonaiv1alpha1.LeptonDeployment{}

	if err := json.Unmarshal(body, &ld.Spec.LeptonDeploymentUserSpec); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "malformed deployment spec: " + err.Error()})
		return
	}
	if err := h.validateCreateInput(c, &ld.Spec.LeptonDeploymentUserSpec); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeValidationError, "message": "invalid deployment spec: " + err.Error()})
		return
	}

	ctx, cancel := util.CreateCtxFromGinCtx(c)
	ph, err := h.phDB.Get(ctx, ld.Spec.PhotonID)
	cancel()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeValidationError, "message": "invalid deployemnt spec: photon " + ld.Spec.PhotonID + " does not exist."})
		return
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
		PhotonImage:                   ph.Spec.Image,
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

	ctx, cancel = util.CreateCtxFromGinCtx(c)
	err = h.ldDB.Create(ctx, ld.Name, ld)
	cancel()
	if err != nil {
		goutil.Logger.Errorw("failed to create deployment",
			"deployment", ld.Name,
			"operation", "create",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create deployment: " + err.Error()})
		return
	}

	ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateStarting

	goutil.Logger.Infow("created deployment",
		"deployment", ld.Name,
		"operation", "create",
	)

	c.JSON(http.StatusOK, NewLeptonDeployment(ld).Output())
}

func (h *DeploymentHandler) List(c *gin.Context) {
	ctx, cancel := util.CreateCtxFromGinCtx(c)
	lds, err := h.ldDB.List(ctx)
	cancel()
	if err != nil {
		goutil.Logger.Errorw("failed to list deployments",
			"operation", "list",
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
	ctx, cancel := util.CreateCtxFromGinCtx(c)
	ld, err := h.ldDB.Get(ctx, did)
	cancel()
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + did + " not found"})
		return
	}

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to read request body: " + err.Error()})
		return
	}

	ldi := &leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	if err := json.Unmarshal(body, &ldi); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "malformed deployment spec: " + err.Error()})
		return
	}
	if err := h.validateUpdateInput(c, ldi); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeValidationError, "message": "invalid deployment spec: " + err.Error()})
		return
	}

	ld.Patch(ldi)
	ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateUpdating

	ctx, cancel = util.CreateCtxFromGinCtx(c)
	err = h.ldDB.Update(ctx, ld.Name, ld)
	cancel()
	if err != nil {
		goutil.Logger.Errorw("failed to update deployment",
			"deployment", ld.GetSpecName(),
			"operation", "update",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to update deployment " + ld.GetSpecName() + ": " + err.Error()})
		return
	}

	goutil.Logger.Infow("updated deployment",
		"deployment", ld.GetSpecName(),
		"operation", "update",
	)

	c.JSON(http.StatusOK, NewLeptonDeployment(ld).Output())
}

func (h *DeploymentHandler) Get(c *gin.Context) {
	did := c.Param("did")
	ctx, cancel := util.CreateCtxFromGinCtx(c)
	ld, err := h.ldDB.Get(ctx, did)
	cancel()
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + did + " not found"})
		return
	}
	c.JSON(http.StatusOK, NewLeptonDeployment(ld).Output())
}

func (h *DeploymentHandler) Delete(c *gin.Context) {
	did := c.Param("did")
	ctx, cancel := util.CreateCtxFromGinCtx(c)
	err := h.ldDB.Delete(ctx, did)
	cancel()
	if err != nil {
		ctx, cancel = util.CreateCtxFromGinCtx(c)
		defer cancel()
		if _, err := h.ldDB.Get(ctx, did); err != nil && apierrors.IsNotFound(err) {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + did + " not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete deployment " + did + ": " + err.Error()})
		return
	}

	goutil.Logger.Infow("deleted deployment",
		"deployment", did,
		"operation", "delete",
	)

	c.Status(http.StatusOK)
}

func (h *DeploymentHandler) validateCreateInput(c *gin.Context, ld *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
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

	if h.phDB == nil { // for testing
		return nil
	}

	ctx, cancel := util.CreateCtxFromGinCtx(c)
	_, err := h.phDB.Get(ctx, ld.PhotonID)
	cancel()
	if err != nil {
		return fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}
	return nil
}

func (h *DeploymentHandler) validateUpdateInput(c *gin.Context, ld *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
	valid := false
	if ld.ResourceRequirement.MinReplicas > 0 {
		valid = true
	}
	if ld.PhotonID != "" {
		ctx, cancel := util.CreateCtxFromGinCtx(c)
		_, err := h.phDB.Get(ctx, ld.PhotonID)
		cancel()
		if err != nil {
			return fmt.Errorf("photon %s does not exist", ld.PhotonID)
		}
		valid = true
	}
	if !valid {
		return fmt.Errorf("no valid field to patch")
	}
	return nil
}
