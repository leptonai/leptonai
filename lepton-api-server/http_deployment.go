package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

func deploymentPostHandler(c *gin.Context) {
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	ld := &leptonaiv1alpha1.LeptonDeployment{}

	if err := json.Unmarshal(body, &ld.Spec.LeptonDeploymentUserSpec); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if err := validateDeploymentInput(&ld.Spec.LeptonDeploymentUserSpec); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "invalid deployment metadata: " + err.Error()})
		return
	}

	ph := photonDB.GetByID(ld.Spec.PhotonID)
	if ph == nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "photon " + ld.Spec.PhotonID + " does not exist."})
		return
	}

	did := util.HexHash(body)
	ld.SetID(did)
	ld.Spec.Photon = &ph.Spec

	ldcr, err := CreateLeptonDeploymentCR(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create deployment CR: " + err.Error()})
		return
	}

	ownerref := util.GetOwnerRefFromUnstructured(ldcr)

	err = createDeployment(ld, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create deployment: " + err.Error()})
		return
	}

	err = createService(ld, ph, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create service: " + err.Error()})
		return
	}

	err = createDeploymentIngress(ld, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create ingress: " + err.Error()})
		return
	}

	cr, err := ReadLeptonDeploymentCR(ld.GetUniqName())
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create deployment CR: " + err.Error()})
		return
	}
	cr.Status.State = leptonaiv1alpha1.LeptonDeploymentStateStarting

	deploymentDB.Add(cr)

	c.JSON(http.StatusOK, httpapi.NewLeptonDeployment(ld).Output())
}

func deploymentListHandler(c *gin.Context) {
	lds := deploymentDB.GetAll()
	ldos := make([]*httpapi.LeptonDeployment, 0, len(lds))
	for _, ld := range lds {
		ldos = append(ldos, httpapi.NewLeptonDeployment(ld).Output())
	}
	c.JSON(http.StatusOK, ldos)
}

func deploymentPatchHandler(c *gin.Context) {
	did := c.Param("did")
	ld := deploymentDB.GetByID(did)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "deployment " + did + " does not exist."})
		return
	}

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	ldi := &leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	if err := json.Unmarshal(body, &ldi); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if err := validatePatchInput(ldi); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "invalid patch metadata: " + err.Error()})
		return
	}

	ld.Patch(ldi)
	ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateUpdating

	_, err = PatchLeptonDeploymentCR(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to patch deployment CR " + ld.GetName() + ": " + err.Error()})
		return
	}

	err = patchDeployment(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to patch deployment " + ld.GetName() + ": " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, httpapi.NewLeptonDeployment(ld).Output())
}

func deploymentGetHandler(c *gin.Context) {
	did := c.Param("did")
	ld := deploymentDB.GetByID(did)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "deployment " + did + " does not exist."})
		return
	}

	c.JSON(http.StatusOK, httpapi.NewLeptonDeployment(ld).Output())
}

func deploymentDeleteHandler(c *gin.Context) {
	did := c.Param("did")
	ld := deploymentDB.GetByID(did)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "deployment " + did + " does not exist."})
		return
	}

	err := DeleteLeptonDeploymentCR(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to delete deployment " + did + " crd: " + err.Error()})
		return
	}

	deploymentDB.Delete(ld)
	c.Status(http.StatusOK)
}

func validateDeploymentInput(ld *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
	if !util.ValidateName(ld.Name) {
		return fmt.Errorf("invalid name %s: %s", ld.Name, util.NameInvalidMessage)
	}
	if ld.ResourceRequirement.CPU <= 0 {
		return fmt.Errorf("cpu must be positive")
	}
	if ld.ResourceRequirement.Memory <= 0 {
		return fmt.Errorf("memory must be positive")
	}
	if ld.ResourceRequirement.MinReplicas <= 0 {
		return fmt.Errorf("min replicas must be positive")
	}
	ph := photonDB.GetByID(ld.PhotonID)
	if ph == nil {
		return fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}
	return nil
}

func validatePatchInput(ld *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
	valid := false
	if ld.ResourceRequirement.MinReplicas > 0 {
		valid = true
	}
	if ld.PhotonID != "" {
		ph := photonDB.GetByID(ld.PhotonID)
		if ph == nil {
			return fmt.Errorf("photon %s does not exist", ld.PhotonID)
		}
		valid = true
	}
	if !valid {
		return fmt.Errorf("no valid field to patch")
	}
	return nil
}
