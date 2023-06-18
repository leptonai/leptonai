package httpapi

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

type DeploymentHandler struct {
	Handler
}

func (h *DeploymentHandler) Create(c *gin.Context) {
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	ld := &leptonaiv1alpha1.LeptonDeployment{}

	if err := json.Unmarshal(body, &ld.Spec.LeptonDeploymentUserSpec); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if err := h.validateCreateInput(&ld.Spec.LeptonDeploymentUserSpec); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "invalid deployment metadata: " + err.Error()})
		return
	}

	ph, err := h.phDB.Get(ld.Spec.PhotonID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "photon " + ld.Spec.PhotonID + " does not exist."})
		return
	}

	ld.Spec.LeptonDeploymentSystemSpec = leptonaiv1alpha1.LeptonDeploymentSystemSpec{
		PhotonName:         ph.GetSpecName(),
		PhotonImage:        ph.Spec.Image,
		BucketName:         h.bucketName,
		PhotonPrefix:       h.photonPrefix,
		ServiceAccountName: h.serviceAccountName,
		RootDomain:         h.rootDomain,
		CellName:           h.cellName,
		CertificateARN:     h.certARN,
	}
	if len(h.apiToken) > 0 {
		ld.Spec.APITokens = []string{h.apiToken}
	}
	ld.Namespace = h.namespace
	ld.Name = ld.GetSpecName()

	if err := h.ldDB.Create(ld.Name, ld); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create deployment: " + err.Error()})
		return
	}

	ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateStarting

	c.JSON(http.StatusOK, NewLeptonDeployment(ld).Output())
}

func (h *DeploymentHandler) List(c *gin.Context) {
	lds, err := h.ldDB.List()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list deployments: " + err.Error()})
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
	ld, err := h.ldDB.Get(did)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "deployment " + did + " does not exist."})
		return
	}

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	ldi := &leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	if err := json.Unmarshal(body, &ldi); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if err := h.validateUpdateInput(ldi); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "invalid update metadata: " + err.Error()})
		return
	}

	ld.Patch(ldi)
	ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateUpdating

	if err := h.ldDB.Update(ld.Name, ld); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to update deployment " + ld.GetSpecName() + ": " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, NewLeptonDeployment(ld).Output())
}

func (h *DeploymentHandler) Get(c *gin.Context) {
	did := c.Param("did")
	ld, err := h.ldDB.Get(did)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "deployment " + did + " does not exist."})
		return
	}
	c.JSON(http.StatusOK, NewLeptonDeployment(ld).Output())
}

func (h *DeploymentHandler) Delete(c *gin.Context) {
	did := c.Param("did")
	if err := h.ldDB.Delete(did); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete deployment " + did + " crd: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}

func (h *DeploymentHandler) validateCreateInput(ld *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
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

		if leptonaiv1alpha1.SupportedShapesAWS[ld.ResourceRequirement.ResourceShape] == nil {
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

	_, err := h.phDB.Get(ld.PhotonID)
	if err != nil {
		return fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}
	return nil
}

func (h *DeploymentHandler) validateUpdateInput(ld *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
	valid := false
	if ld.ResourceRequirement.MinReplicas > 0 {
		valid = true
	}
	if ld.PhotonID != "" {
		_, err := h.phDB.Get(ld.PhotonID)
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
