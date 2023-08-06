package httpapi

import (
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"github.com/gin-gonic/gin"
	appsv1 "k8s.io/api/apps/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
)

type DeploymentTerminationHandler struct {
	Handler
}

func (h *DeploymentTerminationHandler) Get(c *gin.Context) {
	name := c.Param("did")

	deployment := &appsv1.Deployment{}
	err := k8s.MustLoadDefaultClient().Get(c, types.NamespacedName{
		Namespace: h.namespace,
		Name:      name,
	}, deployment)
	if apierrors.IsNotFound(err) {
		goutil.Logger.Debugw("deployment not found",
			"operation", "getTermination",
			"deployment", name,
		)
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + name + " not found"})
		return
	}
	if err != nil {
		goutil.Logger.Errorw("failed to get deployment",
			"operation", "getTermination",
			"deployment", name,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get deployment " + name + ": " + err.Error()})
		return
	}

	terminations, err := getDeploymentTerminations(c, deployment)
	if err != nil {
		goutil.Logger.Errorw("failed to get deployment terminations",
			"operation", "getTermination",
			"deployment", name,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get deployment " + name + "termination issues: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, terminations)
}
