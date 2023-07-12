package httpapi

import (
	"net/http"

	"github.com/leptonai/lepton/lepton-api-server/version"

	"github.com/gin-gonic/gin"
)

type WorkspaceInfo struct {
	version.Info  `json:",inline"`
	WorkspaceName string `json:"workspace_name"`
}

type WorkspaceInfoHandler struct {
	WorkspaceInfo *WorkspaceInfo
}

func NewWorkspaceInfoHandler(workspaceName string) *WorkspaceInfoHandler {
	cih := &WorkspaceInfoHandler{
		WorkspaceInfo: &WorkspaceInfo{
			Info:          version.VersionInfo,
			WorkspaceName: workspaceName,
		},
	}

	return cih
}

func (wi *WorkspaceInfoHandler) HandleGet(c *gin.Context) {
	c.JSON(http.StatusOK, wi.WorkspaceInfo)
}
