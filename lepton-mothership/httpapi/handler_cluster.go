package httpapi

import (
	"log"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/lepton-mothership/cluster"

	"github.com/gin-gonic/gin"
)

func HandleClusterGet(c *gin.Context) {
}

func HandleClusterList(c *gin.Context) {
}

func HandleClusterCreate(c *gin.Context) {
	var cl cluster.Cluster
	err := c.BindJSON(&cl)
	if err != nil {
		log.Println("failed to bind json:", err)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to get cluster: " + err.Error()})
		return
	}

	ncl, err := cluster.Create(cl)
	if err != nil {
		log.Println("failed to create cluster:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create cluster: " + err.Error()})
		return
	}

	c.JSON(201, ncl)
}

func HandleClusterDelete(c *gin.Context) {
	err := cluster.Delete(c.Param("clname"), false)
	if err != nil {
		log.Println("failed to delete cluster:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete cluster: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}

func HandleClusterUpdate(c *gin.Context) {
}
