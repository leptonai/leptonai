package main

import (
	"flag"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

func main() {
	namespace := flag.String("namespace", "default", "namespace to create resources")
	flag.Parse()

	photonNamespace = *namespace
	leptonDeploymentNamespace = *namespace
	deploymentNamespace = *namespace
	serviceNamespace = *namespace
	ingressNamespace = *namespace

	fmt.Println("Starting the Lepton Server on :20863...")

	router := gin.Default()
	router.Use(CORSMiddleware())

	router.GET("/version", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, gin.H{"version": "0.0.1"})
	})
	router.GET("/photons", photonListHandler)
	router.POST("/photons", photonPostHandler)
	router.GET("/photons/:uuid", photonGetHandler)
	router.GET("/photons/:uuid/content", photonDownloadHandler)
	router.DELETE("/photons/:uuid", photonDeleteHandler)

	router.GET("/deployments", deploymentListHandler)
	router.POST("/deployments", deploymentPostHandler)
	router.GET("/deployments/:uuid", deploymentGetHandler)
	router.PATCH("/deployments/:uuid", deploymentPatchHandler)
	router.DELETE("/deployments/:uuid", deploymentDeleteHandler)

	router.Run(":20863")
}

func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
