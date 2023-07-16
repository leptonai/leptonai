package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	"github.com/leptonai/lepton/go-pkg/kv"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/go-pkg/version"
	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"

	"github.com/gin-contrib/requestid"
	ginzap "github.com/gin-contrib/zap"
	"github.com/gin-gonic/gin"
	"gocloud.dev/blob"
	_ "gocloud.dev/blob/s3blob"
)

var photonBucket *blob.Bucket

var (
	certificateARNFlag *string
	rootDomainFlag     *string
	workspaceNameFlag  *string
	apiTokenFlag       *string

	// Workspace level Cloud Resources Flags
	regionFlag                     *string
	bucketTypeFlag, bucketNameFlag *string
	efsIDFlag                      *string
	dynamodbNameFlag               *string

	namespaceFlag    *string
	photonPrefixFlag *string

	serviceAccountNameFlag *string
	prometheusURLFlag      *string

	enableTunaFlag *bool

	storageMountPathFlag *string
	enableStorageFlag    *bool

	requestTimeoutInternal *string
)

const (
	apiServerPort = 20863
	apiServerPath = "/api/"
	rootPath      = "/"

	tunaURL = "https://tuna-dev.vercel.app/"
)

func main() {
	workspaceNameFlag = flag.String("workspace-name", "default", "workspace name")
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
	prometheusURLFlag = flag.String("prometheus-url", "http://kube-prometheus-stack-prometheus.kube-prometheus-stack.svc.cluster.local:9090", "prometheus URL")
	enableTunaFlag = flag.Bool("enable-tuna", false, "enable tuna fine-tuning service")

	enableStorageFlag = flag.Bool("enable-storage", true, "enable storage service")
	storageMountPathFlag = flag.String("storage-mount-path", "/mnt/efs/default", "mount path for storage service")

	requestTimeoutInternal = flag.String(util.RequestTimeoutInternalCtxKey, "1m", "Default request timeout for internal calls")
	flag.Parse()

	if args := flag.Args(); len(args) > 0 && args[0] == "version" {
		fmt.Printf("%+v\n", version.VersionInfo)
		os.Exit(0)
	}

	requestTimeoutInternalDur, err := time.ParseDuration(*requestTimeoutInternal)
	if err != nil {
		log.Fatalln(err)
	}
	pbu := goutil.MustOpenAndAccessBucket(
		context.Background(),
		*bucketTypeFlag,
		*bucketNameFlag,
		*regionFlag,
		*photonPrefixFlag,
	)
	backupPrefix := "workspace-backups"
	bbu := goutil.MustOpenAndAccessBucket(
		context.Background(),
		*bucketTypeFlag,
		*bucketNameFlag,
		*regionFlag,
		backupPrefix,
	)

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
		pbu,
		bbu,
	)

	wih := httpapi.NewWorkspaceInfoHandler(*workspaceNameFlag)

	log.Printf("Starting the Lepton Server on :%d with request timeout %v\n", apiServerPort, requestTimeoutInternalDur)

	router := gin.Default()
	router.Use(CORSMiddleware())
	router.Use(requestid.New())
	router.Use(setRequestTimeoutInternal(requestTimeoutInternalDur))

	logger := goutil.Logger.Desugar()
	// Add a ginzap middleware, which:
	//   - Logs all requests, like a combined access and error log.
	//   - Logs to stdout.
	//   - RFC3339 with UTC time format.
	router.Use(ginzap.Ginzap(logger, time.RFC3339, true))

	// Logs all panic to error log
	//   - stack means whether output the stack info.
	router.Use(ginzap.RecoveryWithZap(logger, true))

	router.GET("/healthz", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, gin.H{"status": "ok", "version": "v1"})
	})

	api := router.Group("/api")

	v1 := api.Group("/v1")

	v1.GET("/workspace", wih.HandleGet)

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
	v1.GET("/deployments/:did/readiness", handler.DeploymentReadinessHandler().Get)
	v1.GET("/deployments/:did/termination", handler.DeploymentTerminationHandler().Get)

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
		v1.HEAD("/storage/default/*path", sh.CheckExists)
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

func setRequestTimeoutInternal(d time.Duration) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Set(util.RequestTimeoutInternalCtxKey, d)
		c.Next()
	}
}
