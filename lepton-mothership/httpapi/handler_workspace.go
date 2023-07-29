package httpapi

import (
	"fmt"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/lepton-mothership/workspace"

	"github.com/gin-gonic/gin"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

func HandleWorkspaceGet(c *gin.Context) {
	wsname := c.Param("wsname")
	lw, err := workspace.Get(c, wsname)
	if err != nil {
		if apierrors.IsNotFound(err) {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "workspace " + wsname + " doesn't exist"})
			return
		}

		goutil.Logger.Errorw("failed to get workspace",
			"workspace", wsname,
			"operation", "get",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get workspace: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, formatWorkspaceOutput(lw))
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
	lws, err := workspace.List(c)
	if err != nil {
		goutil.Logger.Errorw("failed to list workspaces",
			"operation", "list",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list workspaces: " + err.Error()})
		return
	}
	ret := make([]*crdv1alpha1.LeptonWorkspace, len(lws))
	for i, lw := range lws {
		ret[i] = formatWorkspaceOutput(lw)
	}
	c.JSON(http.StatusOK, ret)
}

func HandleWorkspaceCreate(c *gin.Context) {
	var spec crdv1alpha1.LeptonWorkspaceSpec
	err := c.BindJSON(&spec)
	if err != nil {
		goutil.Logger.Debugw("failed to parse json input",
			"operation", "create",
			"error", err,
		)

		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to get workspace: " + err.Error()})
		return
	}

	lw, err := workspace.Create(c, spec)
	if err != nil {
		goutil.Logger.Errorw("failed to create workspace",
			"workspace", spec.Name,
			"operation", "create",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create workspace: " + err.Error()})
		return
	}

	goutil.Logger.Infow("started to create the workspace",
		"workspace", spec.Name,
	)

	c.JSON(http.StatusCreated, lw)
}

func HandleWorkspaceDelete(c *gin.Context) {
	err := workspace.Delete(c.Param("wsname"))
	if err != nil {
		goutil.Logger.Errorw("failed to delete workspace",
			"workspace", c.Param("wsname"),
			"operation", "delete",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete workspace: " + err.Error()})
		return
	}

	goutil.Logger.Infow("started to delete the workspace",
		"workspace", c.Param("wsname"),
	)

	c.Status(http.StatusOK)
}

func HandleWorkspaceUpdate(c *gin.Context) {
	var spec crdv1alpha1.LeptonWorkspaceSpec
	err := c.BindJSON(&spec)
	if err != nil {
		goutil.Logger.Debugw("failed to parse json input",
			"operation", "update",
			"error", err,
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to get workspace: " + err.Error()})
		return
	}

	lw, err := workspace.Update(c, spec)
	if err != nil {
		goutil.Logger.Errorw("failed to update workspace",
			"workspace", spec.Name,
			"operation", "update",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to update workspace: " + err.Error()})
		return
	}

	goutil.Logger.Infow("started to update the workspace",
		"workspace", spec.Name,
	)

	c.JSON(http.StatusOK, lw)
}

func formatWorkspaceOutput(lw *crdv1alpha1.LeptonWorkspace) *crdv1alpha1.LeptonWorkspace {
	return &crdv1alpha1.LeptonWorkspace{
		Spec:   lw.Spec,
		Status: lw.Status,
	}
}