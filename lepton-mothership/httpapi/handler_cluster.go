package httpapi

import (
	"log"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/lepton-api-server/version"
	"github.com/leptonai/lepton/lepton-mothership/cluster"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

func HandleClusterGet(c *gin.Context) {
	cl, err := cluster.Get(c.Param("clname"))
	if err != nil {
		log.Println("failed to get cluster:", err)
		// TODO: check if cluster not found and return user error if not found
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get cluster: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, cl)
}

func HandleClusterGetLogs(c *gin.Context) {
	cname := c.Param("clname")
	job := cluster.Worker.GetJob(cname)
	if job == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "operation of the cluster is not running"})
		return
	}
	c.String(http.StatusOK, job.GetLog())
}

func HandleClusterList(c *gin.Context) {
	cls, err := cluster.List()
	if err != nil {
		log.Println("failed to list clusters:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list clusters: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, cls)
}

// TODO: make this configurable, or derive
const (
	defaultProvider = "aws"
	defaultRegion   = "us-east-1"
)

func HandleClusterCreate(c *gin.Context) {
	var spec crdv1alpha1.LeptonClusterSpec
	err := c.BindJSON(&spec)
	if err != nil {
		log.Println("failed to bind json:", err)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to parse input: " + err.Error()})
		return
	}

	if spec.Provider == "" {
		spec.Provider = defaultProvider
	}
	if spec.Region == "" {
		spec.Region = defaultRegion
	}
	spec.GitRef = version.VersionInfo.GitCommit

	cl, err := cluster.Create(spec)
	if err != nil {
		log.Println("failed to create cluster:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create cluster: " + err.Error()})
		return
	}

	c.JSON(http.StatusCreated, cl)
}

func HandleClusterDelete(c *gin.Context) {
	err := cluster.Delete(c.Param("clname"), true)
	if err != nil {
		log.Println("failed to delete cluster:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete cluster: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}

func HandleClusterUpdate(c *gin.Context) {
	var spec crdv1alpha1.LeptonClusterSpec
	err := c.BindJSON(&spec)
	if err != nil {
		log.Println("failed to bind json:", err)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to parse input: " + err.Error()})
		return
	}

	if spec.Provider == "" {
		spec.Provider = defaultProvider
	}
	if spec.Region == "" {
		spec.Region = defaultRegion
	}
	spec.GitRef = version.VersionInfo.GitCommit

	cl, err := cluster.Update(spec)
	if err != nil {
		log.Println("failed to update cluster:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to update cluster: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, cl)
}
