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
	if ld.validateDeployment() != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "invalid deployment metadata: " + ld.validateDeployment().Error()})
		return
	}

	photonMapRWLock.RLock()
	photon := photonById[ld.PhotonID]
	photonMapRWLock.RUnlock()
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

	deploymentMapRWLock.Lock()
	deploymentById[uuid] = &ld
	deploymentByName[ld.Name] = &ld
	deploymentMapRWLock.Unlock()

	if err := updateLeptonIngress(listAllLeptonDeployments()); err != nil {
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
	// TODO: have a well organized json return value
	ret := make([]*LeptonDeployment, 0)
	deploymentMapRWLock.RLock()
	for _, metadata := range deploymentById {
		ret = append(ret, metadata)
	}
	deploymentMapRWLock.RUnlock()

	c.JSON(http.StatusOK, ret)
}

func deploymentPatchHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	deploymentMapRWLock.RLock()
	ld := deploymentById[uuid]
	deploymentMapRWLock.RUnlock()
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
	if metadata.validatePatch() != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "invalid patch metadata: " + metadata.validateDeployment().Error()})
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
	deploymentMapRWLock.RLock()
	metadata := deploymentById[uuid]
	deploymentMapRWLock.RUnlock()
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "deployment " + uuid + " does not exist."})
		return
	}

	c.JSON(http.StatusOK, metadata)
}

func deploymentDeleteHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	deploymentMapRWLock.RLock()
	metadata := deploymentById[uuid]
	deploymentMapRWLock.RUnlock()
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "deployment " + uuid + " does not exist."})
		return
	}

	err := DeleteLeptonDeploymentCR(metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to delete deployment " + uuid + " crd: " + err.Error()})
		return
	}

	deploymentMapRWLock.Lock()
	delete(deploymentById, uuid)
	delete(deploymentByName, metadata.Name)
	deploymentMapRWLock.Unlock()

	c.Status(http.StatusOK)
}
