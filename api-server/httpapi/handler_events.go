package httpapi

import (
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"github.com/gin-gonic/gin"
)

type DeploymentEventHandler struct {
	Handler
}

func (h *DeploymentEventHandler) Get(c *gin.Context) {
	name := c.Param("did")
	events, err := k8s.ListDeploymentEvents(c, h.namespace, name)
	if err != nil {
		goutil.Logger.Errorw("failed to get events",
			"operation", "getDeploymentEvents",
			"deployment", name,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get events for " + name + ": " + err.Error()})
		return
	}

	les := convertK8sEventsToLeptonDeploymentEvents(*events)
	c.JSON(http.StatusOK, les)
}
