package httpapi

import (
	"net/http"

	"github.com/leptonai/lepton/api-server/quota"
	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/go-pkg/version"

	"github.com/gin-gonic/gin"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

type WorkspaceInfo struct {
	version.Info   `json:",inline"`
	WorkspaceName  string         `json:"workspace_name"`
	WorkspaceState WorkspaceState `json:"workspace_state"`

	ResourceQuota ResourceQuota `json:"resource_quota"`
}

// ResourceQuota is a struct that contains the limit and used resources
type ResourceQuota struct {
	// Limit is the limit of resources
	Limit quota.TotalResource `json:"limit"`
	// Used is the used resources
	Used quota.TotalResource `json:"used"`
}

type WorkspaceState string

const (
	WorkspaceStateNormal     WorkspaceState = "normal"
	WorkspaceStatePaused     WorkspaceState = "paused"
	WorkspaceStateTerminated WorkspaceState = "terminated"
)

type WorkspaceInfoHandler struct {
	Handler
	WorkspaceInfo *WorkspaceInfo
}

func NewWorkspaceInfoHandler(h Handler, workspaceName string, workspaceState WorkspaceState) *WorkspaceInfoHandler {
	cih := &WorkspaceInfoHandler{
		Handler: h,
		WorkspaceInfo: &WorkspaceInfo{
			Info:           version.VersionInfo,
			WorkspaceName:  workspaceName,
			WorkspaceState: workspaceState,
		},
	}

	return cih
}

func (wi *WorkspaceInfoHandler) HandleGet(c *gin.Context) {
	q, err := k8s.GetResourceQuota(c, wi.namespace, "quota-"+wi.workspaceName)
	if err != nil && !apierrors.IsNotFound(err) {
		goutil.Logger.Errorw("failed to get resource quota",
			"operation", "getResourceQuota",
			"workspace", wi.WorkspaceInfo.WorkspaceName,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get resource quota: " + err.Error()})
		return
	}
	wi.WorkspaceInfo.ResourceQuota.Limit = quota.GetTotalResource(q.Status.Hard)
	wi.WorkspaceInfo.ResourceQuota.Used = quota.GetTotalResource(q.Status.Used)

	c.JSON(http.StatusOK, wi.WorkspaceInfo)
}
