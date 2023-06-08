package httpapi

import (
	"log"

	"github.com/gin-gonic/gin"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
)

func HandleClusterGet(c *gin.Context) {
}

func HandleClusterList(c *gin.Context) {
}

func HandleClusterCreate(c *gin.Context) {
	clusterName := "fix-me"
	err := terraform.CreateWorkspace(clusterName)
	if err != nil {
		log.Fatal(err)
	}

	// TODO: clone the required (or latest) version of terraform code from the git repo
	// TODO: run install.sh
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
