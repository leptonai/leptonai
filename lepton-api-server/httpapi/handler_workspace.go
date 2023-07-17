package httpapi

import (
	"net/http"

	"github.com/leptonai/lepton/go-pkg/version"

	"github.com/gin-gonic/gin"
)

type WorkspaceInfo struct {
	version.Info   `json:",inline"`
	WorkspaceName  string         `json:"workspace_name"`
	WorkspaceState WorkspaceState `json:"workspace_state"`
}

type WorkspaceState string

const (
	WorkspaceStateReady      WorkspaceState = "ready"
	WorkspaceStatePaused     WorkspaceState = "paused"
	WorkspaceStateTerminated WorkspaceState = "terminated"
)

type WorkspaceInfoHandler struct {
	WorkspaceInfo *WorkspaceInfo
}

func NewWorkspaceInfoHandler(workspaceName string, workspaceState WorkspaceState) *WorkspaceInfoHandler {
	cih := &WorkspaceInfoHandler{
		WorkspaceInfo: &WorkspaceInfo{
			Info:           version.VersionInfo,
			WorkspaceName:  workspaceName,
			WorkspaceState: workspaceState,
		},
	}

	return cih
}

func (wi *WorkspaceInfoHandler) HandleGet(c *gin.Context) {
	c.JSON(http.StatusOK, wi.WorkspaceInfo)
}
