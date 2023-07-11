package httpapi

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/go-git/go-git/v5/plumbing"
	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/lepton-mothership/cluster"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"
	"github.com/leptonai/lepton/lepton-mothership/util"
	apierrors "k8s.io/apimachinery/pkg/api/errors"

	"github.com/gin-gonic/gin"
)

const defaultGetTimeout = time.Minute

func HandleClusterGet(c *gin.Context) {
	clname := c.Param("clname")
	ctx, cancel := context.WithTimeout(context.Background(), defaultGetTimeout)
	cl, err := cluster.Get(ctx, clname)
	cancel()
	if err != nil {
		if apierrors.IsNotFound(err) {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "cluster " + clname + " doesn't exist"})
			return
		}

		util.Logger.Errorw("failed to get cluster",
			"cluster", clname,
			"operation", "get",
			"error", err)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get cluster: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, cl)
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

const defaultListTimeout = time.Minute

func HandleClusterList(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), defaultListTimeout)
	cls, err := cluster.List(ctx)
	cancel()
	if err != nil {
		util.Logger.Errorw("failed to list clusters",
			"operation", "list",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list clusters: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, cls)
}

// TODO: make this configurable, or derive
const (
	defaultProvider = "aws"
	defaultRegion   = "us-east-1"
)

// create is async, so we don't need full duration
const defaultCreateTimeout = time.Minute

func HandleClusterCreate(c *gin.Context) {
	var spec crdv1alpha1.LeptonClusterSpec
	err := c.BindJSON(&spec)
	if err != nil {
		util.Logger.Debugw("failed to parse json input",
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

	ctx, cancel := context.WithTimeout(context.Background(), defaultCreateTimeout)
	cl, err := cluster.Create(ctx, spec)
	cancel()
	if err != nil {
		util.Logger.Errorw("failed to create cluster",
			"cluster", spec.Name,
			"operation", "create",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create cluster: " + err.Error()})
		return
	}
	util.Logger.Infow("started to create the cluster",
		"cluster", spec.Name,
	)

	c.JSON(http.StatusCreated, cl)
}

func HandleClusterDelete(c *gin.Context) {
	err := cluster.Delete(c.Param("clname"), true)
	if err != nil {
		util.Logger.Errorw("failed to delete cluster",
			"cluster", c.Param("clname"),
			"operation", "delete",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete cluster: " + err.Error()})
		return
	}
	util.Logger.Infow("started to delete the cluster",
		"cluster", c.Param("clname"),
	)

	c.Status(http.StatusOK)
}

// update is async, so we don't need full duration
const defaultUpdateTimeout = time.Minute

func HandleClusterUpdate(c *gin.Context) {
	var spec crdv1alpha1.LeptonClusterSpec
	err := c.BindJSON(&spec)
	if err != nil {
		util.Logger.Debugw("failed to parse json input",
			"operation", "update",
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

	ctx, cancel := context.WithTimeout(context.Background(), defaultUpdateTimeout)
	cl, err := cluster.Update(ctx, spec)
	cancel()
	if err != nil {
		util.Logger.Errorw("failed to update cluster",
			"cluster", spec.Name,
			"operation", "update",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to update cluster: " + err.Error()})
		return
	}

	util.Logger.Infow("started to update the cluster",
		"cluster", spec.Name,
	)

	c.JSON(http.StatusOK, cl)
}
