package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	"github.com/leptonai/lepton/go-pkg/kv"
	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/version"
	"gocloud.dev/blob"
	_ "gocloud.dev/blob/s3blob"
)

var photonBucket *blob.Bucket

var (
	certificateARNFlag *string
	clusterNameFlag    *string
	rootDomainFlag     *string
	workspaceNameFlag  *string
	apiTokenFlag       *string

	// Workspace level Cloud Resources Flags
	regionFlag                     *string
	bucketTypeFlag, bucketNameFlag *string
	efsIDFlag                      *string
	dynamodbNameFlag               *string

	photonPrefixFlag *string
	namespaceFlag    *string

	serviceAccountNameFlag *string
	prometheusURLFlag      *string

	enableTunaFlag *bool

	storageMountPathFlag *string
	enableStorageFlag    *bool
)

const (
	apiServerPort = 20863
	apiServerPath = "/api/"
	rootPath      = "/"

	tunaURL = "https://tuna-dev.vercel.app/"
)

func main() {
	clusterNameFlag = flag.String("cluster-name", "testing", "cluster name")
	workspaceNameFlag = flag.String("workspace-name", "", "workspace name")
	namespaceFlag = flag.String("namespace", "default", "namespace to create resources")

	serviceAccountNameFlag = flag.String("service-account-name", "lepton-api-server", "service account name")

	certificateARNFlag = flag.String("certificate-arn", "", "certificate ARN")
	rootDomainFlag = flag.String("root-domain", "", "root domain")

	apiTokenFlag = flag.String("api-token", "", "API token for authentication")
	regionFlag = flag.String("region", "us-east-1", "cluster region")

	bucketTypeFlag = flag.String("bucket-type", "s3", "cloud provider")
	bucketNameFlag = flag.String("bucket-name", "leptonai", "object store bucket name")

	// rename to EFS root handle
	// e.g. fs-12345678:/:fsap-12345678
	efsIDFlag = flag.String("efs-id", "", "EFS ID")

	photonPrefixFlag = flag.String("photon-prefix", "photons", "object store prefix for photon")

	dynamodbNameFlag = flag.String("dynamodb-name", "", "dynamodb table name")
	prometheusURLFlag = flag.String("prometheus-url", "http://prometheus-server.prometheus.svc.cluster.local", "prometheus URL")
	enableTunaFlag = flag.Bool("enable-tuna", false, "enable tuna fine-tuning service")

	enableStorageFlag = flag.Bool("enable-storage", true, "enable storage service")
	storageMountPathFlag = flag.String("storage-mount-path", "/mnt/efs/default", "mount path for storage service")
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
			*regionFlag,
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

	handler := httpapi.New(
		*namespaceFlag,
		*prometheusURLFlag,
		*bucketNameFlag,
		*efsIDFlag,
		*photonPrefixFlag,
		*serviceAccountNameFlag,
		*rootDomainFlag,
		*workspaceNameFlag,
		*certificateARNFlag,
		*apiTokenFlag,
		photonBucket,
	)

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

	v1.GET("/photons", handler.PhotonHanlder().List)
	v1.POST("/photons", handler.PhotonHanlder().Create)
	v1.GET("/photons/:pid", handler.PhotonHanlder().Get)
	v1.GET("/photons/:pid/content", handler.PhotonHanlder().Download)
	v1.DELETE("/photons/:pid", handler.PhotonHanlder().Delete)

	v1.GET("/secrets", handler.SecretHandler().List)
	v1.POST("/secrets", handler.SecretHandler().Create)
	v1.DELETE("/secrets/:key", handler.SecretHandler().Delete)

	v1.GET("/deployments", handler.DeploymentHandler().List)
	v1.POST("/deployments", handler.DeploymentHandler().Create)
	v1.GET("/deployments/:did", handler.DeploymentHandler().Get)
	v1.PATCH("/deployments/:did", handler.DeploymentHandler().Update)
	v1.DELETE("/deployments/:did", handler.DeploymentHandler().Delete)

	v1.GET("/deployments/:did/replicas", handler.ReplicaHandler().List)
	v1.GET("/deployments/:did/replicas/:rid/shell", handler.ReplicaHandler().Shell)
	v1.GET("/deployments/:did/replicas/:rid/log", handler.ReplicaHandler().Log)

	v1.GET("/deployments/:did/replicas/:rid/monitoring/memoryUtil", handler.MonitoringHandler().ReplicaMemoryUtil)
	v1.GET("/deployments/:did/replicas/:rid/monitoring/memoryUsage", handler.MonitoringHandler().ReplicaMemoryUsage)
	v1.GET("/deployments/:did/replicas/:rid/monitoring/memoryTotal", handler.MonitoringHandler().ReplicaMemoryTotal)
	v1.GET("/deployments/:did/replicas/:rid/monitoring/CPUUtil", handler.MonitoringHandler().ReplicaCPUUtil)

	v1.GET("/deployments/:did/replicas/:rid/monitoring/FastAPIQPS", handler.MonitoringHandler().ReplicaFastAPIQPS)
	v1.GET("/deployments/:did/replicas/:rid/monitoring/FastAPILatency", handler.MonitoringHandler().ReplicaFastAPILatency)
	v1.GET("/deployments/:did/replicas/:rid/monitoring/FastAPIByPathQPS", handler.MonitoringHandler().ReplicaFastAPIQPSByPath)
	v1.GET("/deployments/:did/replicas/:rid/monitoring/FastAPIByPathLatency", handler.MonitoringHandler().ReplicaFastAPILatencyByPath)

	v1.GET("/deployments/:did/replicas/:rid/monitoring/GPUMemoryUtil", handler.MonitoringHandler().ReplicaGPUMemoryUtil)
	v1.GET("/deployments/:did/replicas/:rid/monitoring/GPUMemoryUsage", handler.MonitoringHandler().ReplicaGPUMemoryUsage)
	v1.GET("/deployments/:did/replicas/:rid/monitoring/GPUMemoryTotal", handler.MonitoringHandler().ReplicaGPUMemoryTotal)
	v1.GET("/deployments/:did/replicas/:rid/monitoring/GPUUtil", handler.MonitoringHandler().ReplicaGPUUtil)

	v1.GET("/deployments/:did/monitoring/FastAPIQPS", handler.MonitoringHandler().DeploymentFastAPIQPS)
	v1.GET("/deployments/:did/monitoring/FastAPILatency", handler.MonitoringHandler().DeploymentFastAPILatency)
	v1.GET("/deployments/:did/monitoring/FastAPIQPSByPath", handler.MonitoringHandler().DeploymentFastAPIQPSByPath)
	v1.GET("/deployments/:did/monitoring/FastAPILatencyByPath", handler.MonitoringHandler().DeploymentFastAPILatencyByPath)

	v1.GET("/deployments/:did/events", handler.DeploymentEventHandler().Get)

	u, err := url.Parse(tunaURL)
	if err != nil {
		log.Fatal("Cannot parse tuna service URL:", err)
	}

	if *enableTunaFlag {
		kv, err := kv.NewKVDynamoDB(*dynamodbNameFlag, *regionFlag)
		if err != nil {
			log.Fatal("Cannot create DynamoDB KV:", err)
		}

		jh := httpapi.NewJobHandler(u, kv)
		v1.POST("/tuna/job/add", jh.AddJob)
		v1.GET("/tuna/job/get/:id", jh.GetJobByID)
		v1.GET("/tuna/job/list", jh.ListJobs)
		v1.GET("/tuna/job/list/:status", jh.ListJobsByStatus)
		v1.GET("/tuna/job/cancel/:id", jh.CancelJob)
	}

	if *enableStorageFlag {
		sh := httpapi.NewStorageHandler(*handler, *storageMountPathFlag)
		v1.GET("/storage/default/*path", sh.GetFileOrDir)
		v1.POST("/storage/default/*path", sh.CreateFile)
		v1.PUT("/storage/default/*path", sh.CreateDir)
		v1.DELETE("/storage/default/*path", sh.DeleteFileOrDir)
	}

	if *efsIDFlag != "" {
		v1.POST("/syncer", handler.StorageSyncerHandler().Create)
		v1.DELETE("/syncer/:name", handler.StorageSyncerHandler().Delete)
		// TODO: add list and get
	}

	router.Run(fmt.Sprintf(":%d", apiServerPort))
}

func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Origin", "https://dashboard.lepton.ai")
		c.Writer.Header().Set("Access-Control-Allow-Methods",
			"POST, PUT, HEAD, PATCH, GET, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers",
			"X-CSRF-Token, X-Requested-With, Accept, Accept-Version, "+
				"Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, "+
				ingress.HTTPHeaderNameForAuthorization+", "+
				ingress.HTTPHeaderNameForDeployment)

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
