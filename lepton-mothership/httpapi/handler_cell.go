package httpapi

import "github.com/gin-gonic/gin"

func HandleCellList(c *gin.Context) {
}

func HandleCellGet(c *gin.Context) {
}

func HandleCellCreate(c *gin.Context) {
	// use helm to install lepton server and web?? in one namespace in the given cluster
}

func HandleCellDelete(c *gin.Context) {
	// delete all resources in the given cell namespace
	// helm uninstall the lepton server and web??
}

func HandleCellUpdate(c *gin.Context) {
}
