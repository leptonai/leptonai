package httpapi

import (
	"log"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/lepton-mothership/cluster"
	"github.com/leptonai/lepton/lepton-mothership/terraform"

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
	clusterName := "fix-me"
	// TODO: clone the desired version of terraform code from the git repo
	// TODO: delete all lepton resources in Kubernetes (the namespaces?)
	// TODO: run uninstall.sh

	err := terraform.DeleteWorkspace(clusterName)
	if err != nil {
		log.Fatal(err)
	}
}

func HandleClusterUpdate(c *gin.Context) {
}
