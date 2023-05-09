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
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to read request body"})
		return
	}

	var ld LeptonDeployment
	if err := json.Unmarshal(body, &ld); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to parse request body"})
		return
	}

	photonMapRWLock.RLock()
	photon := photonById[ld.PhotonID]
	photonMapRWLock.RUnlock()
	if photon == nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "message": "photon: " + ld.ID + " not found"})
		return
	}

	uuid := hash(body)
	ld.ID = uuid
	now := time.Now()
	ld.CreatedAt = now.UnixMilli()

	ldcr, err := CreateLeptonDeploymentCR(&ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to create deployment in database"})
		return
	}

	ownerref := getOwnerRefFromUnstructured(ldcr)

	err = createDeployment(&ld, photon, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to create deployment"})
		return
	}

	ld.Status.State = "running"

	err = createService(&ld, photon, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to create service"})
		return
	}

	err = createIngress(&ld, ownerref)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to create ingress"})
		return
	}

	externalEndpoint, err := watchForIngressEndpoint(ingressName(&ld))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to create ingress"})
		return
	}
	ld.Status.Endpoint.ExternalEndpoint = externalEndpoint
	ld.Status.Endpoint.InternalEndpoint = fmt.Sprintf("%s.%s.svc.cluster.local:8080", ld.Name, deploymentNamespace)
	err = PatchLeptonDeploymentCR(&ld)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to create ingress"})
		return
	}

	// todo: reconcile on the ingress state and update the public endpoint status of the lepton deployment

	deploymentMapRWLock.Lock()
	deploymentById[uuid] = &ld
	if deploymentByName[ld.Name] == nil {
		deploymentByName[ld.Name] = make(map[string]*LeptonDeployment)
	}
	deploymentByName[ld.Name][uuid] = &ld
	deploymentMapRWLock.Unlock()

	c.JSON(http.StatusOK, gin.H{"status": "OK", "message": "created deployment: " + uniqName(ld.Name, uuid)})
}

func deploymentListHandler(c *gin.Context) {
	// TODO: have a well organized json return value
	ret := "["
	deploymentMapRWLock.RLock()
	for _, metadata := range deploymentById {
		metadataJson, err := json.Marshal(*metadata)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to marshal deployment metadata"})
			deploymentMapRWLock.RUnlock()
			return
		}
		ret += string(metadataJson) + ","
	}
	deploymentMapRWLock.RUnlock()
	if ret[len(ret)-1] == ',' {
		ret = ret[:len(ret)-1]
	}
	ret += "]"

	c.String(http.StatusOK, ret)
}

func deploymentPatchHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	deploymentMapRWLock.RLock()
	metadata := deploymentById[uuid]
	deploymentMapRWLock.RUnlock()
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"status": "Failed", "error": "deployment: " + uuid + " not found"})
		return
	}

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to read request body"})
		return
	}

	var ld LeptonDeployment
	if err := json.Unmarshal(body, &ld); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to parse request body"})
		return
	}

	err = patchDeployment(metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to patch deployment"})
		return
	}

	metadata.ResourceRequirement.MinReplicas = ld.ResourceRequirement.MinReplicas

	c.JSON(http.StatusOK, gin.H{"status": "OK", "message": "deleted " + uuid})
}

func deploymentGetHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	deploymentMapRWLock.RLock()
	metadata := deploymentById[uuid]
	deploymentMapRWLock.RUnlock()
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"status": "Failed", "error": "not found", "message": "deployment: " + uuid + " not found"})
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
		c.JSON(http.StatusNotFound, gin.H{"status": "Failed", "message": "deployment: " + uuid + " not found"})
		return
	}

	err := DeleteLeptonDeploymentCR(metadata)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error(), "message": "failed to delete deployment from database"})
		return
	}

	deploymentMapRWLock.Lock()
	delete(deploymentById, uuid)
	delete(deploymentByName[metadata.Name], uuid)
	deploymentMapRWLock.Unlock()

	c.JSON(http.StatusOK, gin.H{"status": "OK", "message": "deleted " + uuid})
}
