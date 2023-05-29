package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/leptonai/lepton/lepton-api-server/httpapi"
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
	prometheusURLFlag      *string
	certificateARNFlag     *string
	rootDomainFlag         *string
)

func main() {
	bucketTypeFlag = flag.String("bucket-type", "s3", "cloud provider")
	bucketNameFlag = flag.String("bucket-name", "leptonai", "object store bucket name")
	bucketRegionFlag = flag.String("bucket-region", "us-east-1", "object store region")
	photonPrefixFlag = flag.String("photon-prefix", "photons", "object store prefix for photon")
	namespaceFlag = flag.String("namespace", "default", "namespace to create resources")
	serviceAccountNameFlag = flag.String("service-account-name", "lepton-api-server", "service account name")
	prometheusURLFlag = flag.String("prometheus-url", "http://prometheus-server.prometheus.svc.cluster.local", "prometheus URL")
	certificateARNFlag = flag.String("certificate-arn", "", "certificate ARN")
	rootDomainFlag = flag.String("root-domain", "", "root domain")
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
	certificateARN = *certificateARNFlag
	rootDomain = *rootDomainFlag

	initPhotons()
	initDeployments()

	httpapi.Init(*prometheusURLFlag, deploymentDB, photonDB)

	fmt.Println("Starting the Lepton Server on :20863...")

	router := gin.Default()
	router.GET("/healthz", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, gin.H{"status": "ok", "version": "v1"})
	})

	api := router.Group("/api")

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

	v1.GET("/deployments/:uuid/instances", instanceListHandler)
	v1.GET("/deployments/:uuid/instances/:id/shell", instanceShellHandler)
	v1.GET("/deployments/:uuid/instances/:id/log", instanceLogHandler)

	v1.GET("/deployments/:uuid/instances/:id/monitoring/memoryUsage", httpapi.InstanceMemoryUsageHandler)
	v1.GET("/deployments/:uuid/instances/:id/monitoring/memoryTotal", httpapi.InstanceMemoryTotalHandler)
	v1.GET("/deployments/:uuid/instances/:id/monitoring/CPUUtil", httpapi.InstanceCPUUtilHandler)
	v1.GET("/deployments/:uuid/instances/:id/monitoring/FastAPIQPS", httpapi.InstanceFastAPIQPSHandler)
	v1.GET("/deployments/:uuid/instances/:id/monitoring/FastAPILatency", httpapi.InstanceFastAPILatencyHandler)

	v1.GET("/deployments/:uuid/instances/:id/monitoring/GPUMemoryUtil", httpapi.InstanceGPUMemoryUtilHandler)
	v1.GET("/deployments/:uuid/instances/:id/monitoring/GPUUtil", httpapi.InstanceGPUUtilHandler)
	v1.GET("/deployments/:uuid/instances/:id/monitoring/GPUMemoryUsage", httpapi.InstanceGPUMemoryUsageHandler)
	v1.GET("/deployments/:uuid/instances/:id/monitoring/GPUMemoryTotal", httpapi.InstanceGPUMemoryTotalHandler)

	v1.GET("/deployments/:uuid/monitoring/FastAPIQPS", httpapi.DeploymentFastAPIQPSHandler)
	v1.GET("/deployments/:uuid/monitoring/FastAPILatency", httpapi.DeploymentFastAPILatencyHandler)
	v1.GET("/deployments/:uuid/monitoring/FastAPIQPSByPath", httpapi.DeploymentFastAPIQPSByPathHandler)
	v1.GET("/deployments/:uuid/monitoring/FastAPILatencyByPath", httpapi.DeploymentFastAPILatencyByPathHandler)

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
