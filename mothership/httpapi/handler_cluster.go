package httpapi

import (
	"fmt"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/mothership/cluster"
	crdv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"

	"github.com/gin-gonic/gin"
	"github.com/go-git/go-git/v5/plumbing"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
)

func HandleClusterGet(c *gin.Context) {
	clname := c.Param("clname")
	cl, err := cluster.Get(c, clname)
	if err != nil {
		if apierrors.IsNotFound(err) {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "cluster " + clname + " doesn't exist"})
			return
		}

		goutil.Logger.Errorw("failed to get cluster",
			"cluster", clname,
			"operation", "get",
			"error", err)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get cluster: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, formatClusterOutput(cl))
}

func HandleClusterGetLogs(c *gin.Context) {
	cname := c.Param("clname")
	job := cluster.Worker.GetJob(cname)
	if job == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "operation of the cluster is not running"})
		return
	}
	c.String(http.StatusOK, job.GetLog())
}

func HandleClusterGetFailureLog(c *gin.Context) {
	cname := c.Param("clname")
	job := cluster.Worker.GetLastFailedJob(cname)
	if job == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": fmt.Sprintf("job %s has no failure", cname)})
		return
	}
	c.String(http.StatusOK, job.GetLog())
}

func HandleClusterList(c *gin.Context) {
	cls, err := cluster.List(c)
	if err != nil {
		goutil.Logger.Errorw("failed to list clusters",
			"operation", "list",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list clusters: " + err.Error()})
		return
	}
	ret := make([]*crdv1alpha1.LeptonCluster, len(cls))
	for i, cl := range cls {
		ret[i] = formatClusterOutput(cl)
	}
	c.JSON(http.StatusOK, ret)
}

// TODO: make this configurable, or derive
const (
	defaultProvider = "aws"
	defaultRegion   = "us-east-1"
)

func HandleClusterCreate(c *gin.Context) {
	var spec crdv1alpha1.LeptonClusterSpec
	err := c.BindJSON(&spec)
	if err != nil {
		goutil.Logger.Debugw("failed to parse json input",
			"operation", "create",
			"error", err,
		)

		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to parse input: " + err.Error()})
		return
	}

	if spec.Provider == "" {
		spec.Provider = defaultProvider
	}
	if spec.Region == "" {
		spec.Region = defaultRegion
	}
	if spec.GitRef == "" {
		spec.GitRef = string(plumbing.Main)
	}
	if spec.DeploymentEnvironment == "" {
		spec.DeploymentEnvironment = cluster.DeploymentEnvironment
	}

	switch spec.DeploymentEnvironment {
	case cluster.DeploymentEnvironmentValueTest,
		cluster.DeploymentEnvironmentValueDev,
		cluster.DeploymentEnvironmentValueProd:
	default:
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "unknown deployment environment: " + spec.DeploymentEnvironment})
		return
	}

	cl, err := cluster.Create(c, spec)
	if err != nil {
		goutil.Logger.Errorw("failed to create cluster",
			"cluster", spec.Name,
			"operation", "create",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create cluster: " + err.Error()})
		return
	}
	goutil.Logger.Infow("started to create the cluster",
		"cluster", spec.Name,
	)

	c.JSON(http.StatusCreated, formatClusterOutput(cl))
}

func HandleClusterDelete(c *gin.Context) {
	force := c.DefaultQuery("force", "false")
	clName := c.Param("clname")
	lc, err := cluster.Get(c, clName)
	if err != nil {
		if apierrors.IsNotFound(err) {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "cluster " + c.Param("clname") + " doesn't exist"})
			return
		}
		goutil.Logger.Errorw("failed to get cluster",
			"cluster", clName,
			"operation", "delete",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get cluster: " + err.Error()})
		return
	}

	if force != "true" && len(lc.Status.Workspaces) != 0 {
		c.JSON(http.StatusBadRequest, gin.H{
			"code":    httperrors.ErrorCodeInvalidRequest,
			"message": fmt.Sprintf("cluster %s has workspaces %v, please delete them first", clName, lc.Status.Workspaces),
		})
		return
	}

	if err := cluster.Delete(c.Param("clname")); err != nil {
		goutil.Logger.Errorw("failed to delete cluster",
			"cluster", clName,
			"operation", "delete",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete cluster: " + err.Error()})
		return
	}
	goutil.Logger.Infow("started to delete the cluster",
		"cluster", clName,
	)

	c.Status(http.StatusOK)
}

func HandleClusterUpdate(c *gin.Context) {
	var spec crdv1alpha1.LeptonClusterSpec
	err := c.BindJSON(&spec)
	if err != nil {
		goutil.Logger.Debugw("failed to parse json input",
			"operation", "update",
			"error", err,
		)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to parse input: " + err.Error()})
		return
	}

	cl, err := cluster.Update(c, spec)
	if err != nil {
		goutil.Logger.Errorw("failed to update cluster",
			"cluster", spec.Name,
			"operation", "update",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to update cluster: " + err.Error()})
		return
	}

	goutil.Logger.Infow("started to update the cluster",
		"cluster", spec.Name,
	)

	c.JSON(http.StatusOK, cl)
}

func formatClusterOutput(lc *crdv1alpha1.LeptonCluster) *crdv1alpha1.LeptonCluster {
	return &crdv1alpha1.LeptonCluster{
		Spec:   lc.Spec,
		Status: lc.Status,
	}
}
