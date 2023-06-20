package httpapi

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
)

type DeploymentEventHandler struct {
	Handler
}

func (h *DeploymentEventHandler) Get(c *gin.Context) {
	name := c.Param("did")
	events, err := k8s.ListDeploymentEvents(h.namespace, name)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get events for " + name + ": " + err.Error()})
		return
	}

	les := convertK8sEventsToLeptonDeploymentEvents(*events)
	c.JSON(http.StatusOK, les)
}
