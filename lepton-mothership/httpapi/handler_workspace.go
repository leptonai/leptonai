package httpapi

import (
	"fmt"
	"log"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/lepton-mothership/workspace"

	"github.com/gin-gonic/gin"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

func HandleWorkspaceGet(c *gin.Context) {
	wsname := c.Param("wsname")
	// TODO: add context, similar to those in handler_cluster.go
	lw, err := workspace.Get(wsname)
	if err != nil {
		if apierrors.IsNotFound(err) {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "workspace " + wsname + " doesn't exist"})
			return
		}
		log.Println("failed to get workspace:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get workspace: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, lw)
}

func HandleWorkspaceGetLogs(c *gin.Context) {
	wname := c.Param("wsname")
	job := workspace.Worker.GetJob(wname)
	if job == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "operation of the workspace is not running"})
		return
	}
	c.String(http.StatusOK, job.GetLog())
}

func HandleWorkspaceGetFailureLog(c *gin.Context) {
	wname := c.Param("wsname")
	job := workspace.Worker.GetLastFailedJob(wname)
	if job == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": fmt.Sprintf("workspace %s has no failure", wname)})
		return
	}
	c.String(http.StatusOK, job.GetLog())
}

func HandleWorkspaceList(c *gin.Context) {
	lws, err := workspace.List()
	if err != nil {
		log.Println("failed to list workspaces:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list workspaces: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, lws)
}

func HandleWorkspaceCreate(c *gin.Context) {
	var spec crdv1alpha1.LeptonWorkspaceSpec
	err := c.BindJSON(&spec)
	if err != nil {
		log.Println("failed to bind json:", err)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to get workspace: " + err.Error()})
		return
	}

	lw, err := workspace.Create(spec)
	if err != nil {
		log.Println("failed to create workspace:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create workspace: " + err.Error()})
		return
	}

	c.JSON(http.StatusCreated, lw)
}

func HandleWorkspaceDelete(c *gin.Context) {
	err := workspace.Delete(c.Param("wsname"), true)
	if err != nil {
		log.Println("failed to delete workspace:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete workspace: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}

func HandleWorkspaceUpdate(c *gin.Context) {
	var spec crdv1alpha1.LeptonWorkspaceSpec
	err := c.BindJSON(&spec)
	if err != nil {
		log.Println("failed to bind json:", err)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to get workspace: " + err.Error()})
		return
	}

	lw, err := workspace.Update(spec)
	if err != nil {
		log.Println("failed to update workspace:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to update workspace: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, lw)
}
