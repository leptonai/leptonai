package main

import (
	"encoding/json"
	"fmt"
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

	err = createDeployment(&ld, photon, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to create deployment: " + err.Error()})
		return
	}

	err = createService(&ld, photon, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to create service: " + err.Error()})
		return
	}

	err = createIngress(&ld, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to create ingress: " + err.Error()})
		return
	}

	externalEndpoint, err := watchForIngressEndpoint(ingressName(&ld))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to get the external endpoint: " + err.Error()})
		return
	}
	ld.Status.Endpoint.ExternalEndpoint = externalEndpoint
	ld.Status.Endpoint.InternalEndpoint = fmt.Sprintf("%s.%s.svc.cluster.local:8080", ld.Name, deploymentNamespace)
	err = PatchLeptonDeploymentCR(&ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to update the external endpoint to deployment crd: " + err.Error()})
		return
	}

	// todo: reconcile on the ingress state and update the public endpoint status of the lepton deployment

	deploymentMapRWLock.Lock()
	deploymentById[uuid] = &ld
	deploymentByName[ld.Name] = &ld
	deploymentMapRWLock.Unlock()

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
	metadata := deploymentById[uuid]
	deploymentMapRWLock.RUnlock()
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "deployment " + uuid + " does not exist."})
		return
	}

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

	metadata.ResourceRequirement.MinReplicas = ld.ResourceRequirement.MinReplicas
	metadata.Status.State = DeploymentStatePatching

	err = PatchLeptonDeploymentCR(metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to patch deployment CR " + metadata.Name + ": " + err.Error()})
		return
	}

	err = patchDeployment(metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to patch deployment " + metadata.Name + ": " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, metadata)
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
