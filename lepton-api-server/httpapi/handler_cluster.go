package httpapi

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type ClusterInfo struct {
	ClusterName string `json:"cluster_name"`
}

type ClusterInfoHandler struct {
	ClusterInfo ClusterInfo
}

func NewClusterInfoHandler(clusterName string) *ClusterInfoHandler {
	return &ClusterInfoHandler{
		ClusterInfo: ClusterInfo{
			ClusterName: clusterName,
		},
	}
}

func (ci *ClusterInfoHandler) Handle(c *gin.Context) {
	c.JSON(http.StatusOK, ci.ClusterInfo)
}
