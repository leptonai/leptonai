package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"gocloud.dev/blob"
	_ "gocloud.dev/blob/s3blob"
)

var photonBucket *blob.Bucket
var (
	bucketTypeFlag         *string
	bucketNameFlag         *string
	bucketRegionFlag       *string
	photonPrefixFlag       *string
	namespaceFlag          *string
	serviceAccountNameFlag *string
)

func main() {
	bucketTypeFlag = flag.String("bucket-type", "s3", "cloud provider")
	bucketNameFlag = flag.String("bucket-name", "leptonai", "object store bucket name")
	bucketRegionFlag = flag.String("bucket-region", "us-east-1", "object store region")
	photonPrefixFlag = flag.String("photon-prefix", "photons", "object store prefix for photon")
	namespaceFlag = flag.String("namespace", "default", "namespace to create resources")
	serviceAccountNameFlag = flag.String("service-account-name", "lepton-api-server", "service account name")
	flag.Parse()

	// Create and verify the bucket.
	var err error
	photonBucket, err = blob.OpenBucket(context.TODO(),
		fmt.Sprintf("%s://%s?region=%s&prefix=%s/",
			*bucketTypeFlag,
			*bucketNameFlag,
			*bucketRegionFlag,
			*photonPrefixFlag))
	if err != nil {
		panic(err)
	}
	accessible, err := photonBucket.IsAccessible(context.Background())
	if err != nil {
		panic(err)
	}
	if !accessible {
		panic("bucket is not accessible")
	}

	// Set the namespace for various resources.
	photonNamespace = *namespaceFlag
	leptonDeploymentNamespace = *namespaceFlag
	deploymentNamespace = *namespaceFlag
	serviceNamespace = *namespaceFlag
	ingressNamespace = *namespaceFlag

	initPhotons()
	initDeployments()

	fmt.Println("Starting the Lepton Server on :20863...")

	router := gin.Default()
	router.Use(CORSMiddleware())

	api := router.Group("/api")
	api.GET("/healthz", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, gin.H{"status": "ok", "version": "v1"})
	})

	v1 := api.Group("/v1")

	v1.GET("/photons", photonListHandler)
	v1.POST("/photons", photonPostHandler)
	v1.GET("/photons/:uuid", photonGetHandler)
	v1.GET("/photons/:uuid/content", photonDownloadHandler)
	v1.DELETE("/photons/:uuid", photonDeleteHandler)

	v1.GET("/deployments", deploymentListHandler)
	v1.POST("/deployments", deploymentPostHandler)
	v1.GET("/deployments/:uuid", deploymentGetHandler)
	v1.PATCH("/deployments/:uuid", deploymentPatchHandler)
	v1.DELETE("/deployments/:uuid", deploymentDeleteHandler)

	router.Run(":20863")
}

func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE, PATCH")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
