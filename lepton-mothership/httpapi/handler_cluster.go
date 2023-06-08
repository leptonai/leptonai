package httpapi

import (
	"log"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	"github.com/leptonai/lepton/lepton-mothership/git"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
)

func HandleClusterGet(c *gin.Context) {
}

func HandleClusterList(c *gin.Context) {
}

func HandleClusterCreate(c *gin.Context) {
	leptonRepoURL := "https://github.com/leptonai/lepton.git"
	clusterName := "fix-me"
	err := terraform.CreateWorkspace(clusterName)
	if err != nil {
		log.Fatal(err)
	}

	wd, err := os.Getwd()
	if err != nil {
		log.Println("failed to get working directory:", err)
		return
	}
	gitDir := filepath.Join(wd, clusterName, "git")
	err = os.MkdirAll(gitDir, 0750)
	if err != nil {
		log.Println("failed to create working directory:", err)
		return
	}

	// Optimize me: only does one clone for all clusters
	// TODO: switch to desired version of terraform code from the git repo
	err = git.Clone(gitDir, leptonRepoURL)
	if err != nil {
		log.Println("failed to clone the git repo:", err)
		return
	}

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
