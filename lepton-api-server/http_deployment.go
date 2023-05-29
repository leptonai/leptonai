package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"

	"github.com/gin-gonic/gin"
)

func deploymentPostHandler(c *gin.Context) {
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	var ld httpapi.LeptonDeployment
	if err := json.Unmarshal(body, &ld); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if validateDeploymentMetadata(ld) != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "invalid deployment metadata: " + validateDeploymentMetadata(ld).Error()})
		return
	}

	photon := photonDB.GetByID(ld.PhotonID)
	if photon == nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "photon " + ld.PhotonID + " does not exist."})
		return
	}

	uuid := util.HexHash(body)
	ld.ID = uuid
	now := time.Now()
	ld.CreatedAt = now.UnixMilli()
	ld.Status.State = httpapi.DeploymentStateStarting

	ldcr, err := CreateLeptonDeploymentCR(&ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create deployment CR: " + err.Error()})
		return
	}

	ownerref := util.GetOwnerRefFromUnstructured(ldcr)

	err = createDeployment(&ld, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create deployment: " + err.Error()})
		return
	}

	err = createService(&ld, photon, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create service: " + err.Error()})
		return
	}

	deploymentDB.Add(&ld)

	if err := updateLeptonIngress(deploymentDB.GetAll()); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to update ingress: " + err.Error()})
	}

	err = createDeploymentIngress(&ld, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create ingress: " + err.Error()})
		return
	}

	_, err = PatchLeptonDeploymentCR(&ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to update the external endpoint to deployment crd: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, ld)
}

func deploymentListHandler(c *gin.Context) {
	c.JSON(http.StatusOK, deploymentDB.GetAll())
}

func deploymentPatchHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	ld := deploymentDB.GetByID(uuid)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "deployment " + uuid + " does not exist."})
		return
	}

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	var metadata httpapi.LeptonDeployment
	if err := json.Unmarshal(body, &metadata); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if validatePatchMetadata(metadata) != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "invalid patch metadata: " + validateDeploymentMetadata(metadata).Error()})
		return
	}

	ld.Merge(&metadata)
	ld.Status.State = httpapi.DeploymentStateUpdating

	_, err = PatchLeptonDeploymentCR(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to patch deployment CR " + ld.Name + ": " + err.Error()})
		return
	}

	err = patchDeployment(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to patch deployment " + ld.Name + ": " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, ld)
}

func deploymentGetHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	ld := deploymentDB.GetByID(uuid)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "deployment " + uuid + " does not exist."})
		return
	}

	c.JSON(http.StatusOK, ld)
}

func deploymentDeleteHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	ld := deploymentDB.GetByID(uuid)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "deployment " + uuid + " does not exist."})
		return
	}

	err := DeleteLeptonDeploymentCR(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to delete deployment " + uuid + " crd: " + err.Error()})
		return
	}

	deploymentDB.Delete(ld)
	c.Status(http.StatusOK)
}

func validateDeploymentMetadata(ld httpapi.LeptonDeployment) error {
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

func validatePatchMetadata(ld httpapi.LeptonDeployment) error {
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
