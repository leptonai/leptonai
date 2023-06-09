package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/version"
	"gocloud.dev/blob"
	_ "gocloud.dev/blob/s3blob"
)

var photonBucket *blob.Bucket

var (
	clusterNameFlag    *string
	certificateARNFlag *string
	rootDomainFlag     *string
	apiTokenFlag       *string

	bucketTypeFlag, bucketNameFlag, bucketRegionFlag *string
	photonPrefixFlag                                 *string
	namespaceFlag                                    *string
	serviceAccountNameFlag                           *string
	prometheusURLFlag                                *string
)

const (
	apiServerPort = 20863
	apiServerPath = "/api/"
	rootPath      = "/"
)

func main() {
	clusterNameFlag = flag.String("cluster-name", "testing", "cluster name")
	certificateARNFlag = flag.String("certificate-arn", "", "certificate ARN")
	rootDomainFlag = flag.String("root-domain", "", "root domain")
	apiTokenFlag = flag.String("api-token", "", "API token for authentication")

	bucketTypeFlag = flag.String("bucket-type", "s3", "cloud provider")
	bucketNameFlag = flag.String("bucket-name", "leptonai", "object store bucket name")
	bucketRegionFlag = flag.String("bucket-region", "us-east-1", "object store region")
	photonPrefixFlag = flag.String("photon-prefix", "photons", "object store prefix for photon")

	namespaceFlag = flag.String("namespace", "default", "namespace to create resources")
	serviceAccountNameFlag = flag.String("service-account-name", "lepton-api-server", "service account name")

	prometheusURLFlag = flag.String("prometheus-url", "http://prometheus-server.prometheus.svc.cluster.local", "prometheus URL")
	flag.Parse()

	if args := flag.Args(); len(args) > 0 && args[0] == "version" {
		fmt.Printf("%+v\n", version.VersionInfo)
		os.Exit(0)
	}

	// Create and verify the bucket.
	var err error
	photonBucket, err = blob.OpenBucket(context.TODO(),
		fmt.Sprintf("%s://%s?region=%s&prefix=%s/",
			*bucketTypeFlag,
			*bucketNameFlag,
			*bucketRegionFlag,
			*photonPrefixFlag))
	if err != nil {
		log.Fatalln(err)
	}
	accessible, err := photonBucket.IsAccessible(context.Background())
	if err != nil {
		log.Fatalln(err)
	}
	if !accessible {
		log.Fatalln("bucket is not accessible")
	}

	// Set the namespace for various resources.
	ingressNamespace = *namespaceFlag
	certificateARN = *certificateARNFlag
	rootDomain = *rootDomainFlag
	apiToken = *apiTokenFlag

	initPhotons()
	initDeployments()
	mustInitAPIServerIngress()
	mustInitUnauthorizedErrorIngress()

	httpapi.Init(*prometheusURLFlag, *namespaceFlag, deploymentDB, photonDB)
	cih := httpapi.NewClusterInfoHandler(*clusterNameFlag)

	log.Printf("Starting the Lepton Server on :%d...\n", apiServerPort)

	router := gin.Default()
	router.Use(CORSMiddleware())
	router.Use(requestid.New())
	router.GET("/healthz", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, gin.H{"status": "ok", "version": "v1"})
	})

	api := router.Group("/api")

	v1 := api.Group("/v1")

	v1.GET("/cluster", cih.Handle)

	v1.GET("/photons", photonListHandler)
	v1.POST("/photons", photonPostHandler)
	v1.GET("/photons/:pid", photonGetHandler)
	v1.GET("/photons/:pid/content", photonDownloadHandler)
	v1.DELETE("/photons/:pid", photonDeleteHandler)

	v1.GET("/deployments", deploymentListHandler)
	v1.POST("/deployments", deploymentPostHandler)
	v1.GET("/deployments/:did", deploymentGetHandler)
	v1.PATCH("/deployments/:did", deploymentPatchHandler)
	v1.DELETE("/deployments/:did", deploymentDeleteHandler)

	v1.GET("/deployments/:did/instances", httpapi.InstanceListHandler)
	v1.GET("/deployments/:did/instances/:iid/shell", httpapi.InstanceShellHandler)
	v1.GET("/deployments/:did/instances/:iid/log", httpapi.InstanceLogHandler)

	v1.GET("/deployments/:did/instances/:iid/monitoring/memoryUtil", httpapi.InstanceMemoryUtilHandler)
	v1.GET("/deployments/:did/instances/:iid/monitoring/memoryUsage", httpapi.InstanceMemoryUsageHandler)
	v1.GET("/deployments/:did/instances/:iid/monitoring/memoryTotal", httpapi.InstanceMemoryTotalHandler)
	v1.GET("/deployments/:did/instances/:iid/monitoring/CPUUtil", httpapi.InstanceCPUUtilHandler)

	v1.GET("/deployments/:did/instances/:iid/monitoring/FastAPIQPS", httpapi.InstanceFastAPIQPSHandler)
	v1.GET("/deployments/:did/instances/:iid/monitoring/FastAPILatency", httpapi.InstanceFastAPILatencyHandler)
	v1.GET("/deployments/:did/instances/:iid/monitoring/FastAPIByPathQPS", httpapi.InstanceFastAPIQPSByPathHandler)
	v1.GET("/deployments/:did/instances/:iid/monitoring/FastAPIByPathLatency", httpapi.InstanceFastAPILatencyByPathHandler)

	v1.GET("/deployments/:did/instances/:iid/monitoring/GPUMemoryUtil", httpapi.InstanceGPUMemoryUtilHandler)
	v1.GET("/deployments/:did/instances/:iid/monitoring/GPUMemoryUsage", httpapi.InstanceGPUMemoryUsageHandler)
	v1.GET("/deployments/:did/instances/:iid/monitoring/GPUMemoryTotal", httpapi.InstanceGPUMemoryTotalHandler)
	v1.GET("/deployments/:did/instances/:iid/monitoring/GPUUtil", httpapi.InstanceGPUUtilHandler)

	v1.GET("/deployments/:did/monitoring/FastAPIQPS", httpapi.DeploymentFastAPIQPSHandler)
	v1.GET("/deployments/:did/monitoring/FastAPILatency", httpapi.DeploymentFastAPILatencyHandler)
	v1.GET("/deployments/:did/monitoring/FastAPIQPSByPath", httpapi.DeploymentFastAPIQPSByPathHandler)
	v1.GET("/deployments/:did/monitoring/FastAPILatencyByPath", httpapi.DeploymentFastAPILatencyByPathHandler)

	router.Run(fmt.Sprintf(":%d", apiServerPort))
}

func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Origin", "https://dashboard.lepton.ai")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, PUT, HEAD, PATCH, GET, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
