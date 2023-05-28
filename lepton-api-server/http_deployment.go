package main

import (
	"encoding/json"
	"io"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

func deploymentPostHandler(c *gin.Context) {
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	var ld LeptonDeployment
	if err := json.Unmarshal(body, &ld); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if ld.validateDeploymentMetadata() != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "invalid deployment metadata: " + ld.validateDeploymentMetadata().Error()})
		return
	}

	photon := photonDB.GetByID(ld.PhotonID)
	if photon == nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "photon " + ld.PhotonID + " does not exist."})
		return
	}

	uuid := hash(body)
	ld.ID = uuid
	now := time.Now()
	ld.CreatedAt = now.UnixMilli()
	ld.Status.State = DeploymentStateStarting

	ldcr, err := CreateLeptonDeploymentCR(&ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to create deployment CR: " + err.Error()})
		return
	}

	ownerref := getOwnerRefFromUnstructured(ldcr)

	err = createDeployment(&ld, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to create deployment: " + err.Error()})
		return
	}

	err = createService(&ld, photon, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to create service: " + err.Error()})
		return
	}

	deploymentDB.Add(&ld)

	if err := updateLeptonIngress(deploymentDB.GetAll()); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to update ingress: " + err.Error()})
	}

	err = createDeploymentIngress(&ld, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to create ingress: " + err.Error()})
		return
	}

	_, err = PatchLeptonDeploymentCR(&ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to update the external endpoint to deployment crd: " + err.Error()})
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
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "deployment " + uuid + " does not exist."})
		return
	}

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	var metadata LeptonDeployment
	if err := json.Unmarshal(body, &metadata); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if metadata.validatePatchMetadata() != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "invalid patch metadata: " + metadata.validateDeploymentMetadata().Error()})
		return
	}

	ld.merge(&metadata)
	ld.Status.State = DeploymentStateUpdating

	_, err = PatchLeptonDeploymentCR(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to patch deployment CR " + ld.Name + ": " + err.Error()})
		return
	}

	err = patchDeployment(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to patch deployment " + ld.Name + ": " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, ld)
}

func deploymentGetHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	ld := deploymentDB.GetByID(uuid)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "deployment " + uuid + " does not exist."})
		return
	}

	c.JSON(http.StatusOK, ld)
}

func deploymentDeleteHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	ld := deploymentDB.GetByID(uuid)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "deployment " + uuid + " does not exist."})
		return
	}

	err := DeleteLeptonDeploymentCR(ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to delete deployment " + uuid + " crd: " + err.Error()})
		return
	}

	deploymentDB.Delete(ld)
	c.Status(http.StatusOK)
}
