package httpapi

import (
	"context"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"github.com/gin-gonic/gin"
	appsv1 "k8s.io/api/apps/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
)

type DeploymentReadinessHandler struct {
	Handler
}

func (h *DeploymentReadinessHandler) Get(c *gin.Context) {
	name := c.Param("did")
	deployment := &appsv1.Deployment{}
	err := k8s.Client.Get(context.Background(), types.NamespacedName{
		Namespace: h.namespace,
		Name:      name,
	}, deployment)
	if err != nil {
		if apierrors.IsNotFound(err) {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + name + " not found"})
			return
		}

		goutil.Logger.Errorw("failed to get deployment",
			"operation", "getRedinessIssue",
			"deployment", name,
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get deployment " + name + ": " + err.Error()})
		return
	}

	issue, err := getDeploymentReadinessIssue(deployment)
	if err != nil {
		goutil.Logger.Errorw("failed to get deployment readiness issues",
			"operation", "getRedinessIssue",
			"deployment", name,
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get deployment " + name + "readiness issues: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, issue)
}
