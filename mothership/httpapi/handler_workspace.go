package httpapi

import (
	"fmt"
	"net/http"

	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/httperrors"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/mothership/metrics"
	"github.com/leptonai/lepton/mothership/workspace"

	"github.com/gin-gonic/gin"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

var Workspace *workspace.Workspace

var (
	// TODO: get from the config. Stop using global variables.
	RootDomain          string
	SharedAlbRootDomain string
)

const (
	// Add this query parameter key to check if the workspace is ready.
	CheckReadinessQueryKey = "check_readiness"
)

func HandleWorkspaceGet(c *gin.Context) {
	wsname := c.Param("wsname")
	lw, err := Workspace.Get(c, wsname)
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

	ws := formatWorkspaceOutput(lw)
	maybeUpdateWorkspaceReadiness(c, ws)

	c.JSON(http.StatusOK, ws)
}

func HandleWorkspaceGetLogs(c *gin.Context) {
	wname := c.Param("wsname")
	job := Workspace.Worker.GetJob(wname)
	if job == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "operation of the workspace is not running"})
		return
	}
	l := job.GetLog()
	metrics.TrackWorkspaceLogsResponse(float64(len(l)))
	c.String(http.StatusOK, l)
}

func HandleWorkspaceGetFailureLog(c *gin.Context) {
	wname := c.Param("wsname")
	job := Workspace.Worker.GetLastFailedJob(wname)
	if job == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": fmt.Sprintf("workspace %s has no failure", wname)})
		return
	}
	l := job.GetLog()
	metrics.TrackWorkspaceLogsResponse(float64(len(l)))
	c.String(http.StatusOK, l)
}

func HandleWorkspaceList(c *gin.Context) {
	lws, err := Workspace.List(c)
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
		maybeUpdateWorkspaceReadiness(c, ret[i])
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

	lw, err := Workspace.Create(c, spec)
	if err != nil {
		goutil.Logger.Infow("failed to create workspace",
			"workspace", spec.Name,
			"operation", "create",
			"error", err,
		)

		return
	}

	goutil.Logger.Infow("started to create the workspace",
		"workspace", spec.Name,
	)

	c.JSON(http.StatusCreated, formatWorkspaceOutput(lw))
}

func HandleWorkspaceDelete(c *gin.Context) {
	err := Workspace.Delete(c.Param("wsname"))
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

	lw, err := Workspace.Update(c, spec)
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

func maybeUpdateWorkspaceReadiness(c *gin.Context, ws *crdv1alpha1.LeptonWorkspace) {
	if c.Query(CheckReadinessQueryKey) != "true" {
		return
	}

	if ws.Status.State == crdv1alpha1.WorkspaceOperationalStateReady {
		remoteURL := fmt.Sprintf("https://%s.%s/api/v1", ws.Spec.Name, RootDomain)
		c := goclient.New(remoteURL, ws.Spec.APIToken)
		_, err := c.Workspace().Info()
		if err != nil {
			ws.Status.State = crdv1alpha1.WorkspaceOperationalStateNotReady
		}
	}
}
