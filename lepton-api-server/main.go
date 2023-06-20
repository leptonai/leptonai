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
	"github.com/leptonai/lepton/go-pkg/kv"
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
	cellNameFlag       *string
	apiTokenFlag       *string

	bucketTypeFlag, bucketNameFlag, bucketRegionFlag *string
	photonPrefixFlag                                 *string
	namespaceFlag                                    *string
	serviceAccountNameFlag                           *string
	prometheusURLFlag                                *string
	enableTunaFlag                                   *bool
)

const (
	apiServerPort = 20863
	apiServerPath = "/api/"
	rootPath      = "/"

	tunaURL = "https://tuna-tunaml.vercel.app"
)

func main() {
	clusterNameFlag = flag.String("cluster-name", "testing", "cluster name")
	certificateARNFlag = flag.String("certificate-arn", "", "certificate ARN")
	rootDomainFlag = flag.String("root-domain", "", "root domain")
	cellNameFlag = flag.String("cell-name", "", "cell name")
	apiTokenFlag = flag.String("api-token", "", "API token for authentication")

	bucketTypeFlag = flag.String("bucket-type", "s3", "cloud provider")
	bucketNameFlag = flag.String("bucket-name", "leptonai", "object store bucket name")
	bucketRegionFlag = flag.String("bucket-region", "us-east-1", "object store region")
	photonPrefixFlag = flag.String("photon-prefix", "photons", "object store prefix for photon")

	namespaceFlag = flag.String("namespace", "default", "namespace to create resources")
	serviceAccountNameFlag = flag.String("service-account-name", "lepton-api-server", "service account name")

	prometheusURLFlag = flag.String("prometheus-url", "http://prometheus-server.prometheus.svc.cluster.local", "prometheus URL")
	enableTunaFlag = flag.Bool("enable-tuna", false, "enable tuna fine-tuning service")
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

	mustInitAPIServerIngress()
	mustInitUnauthorizedErrorIngress()

	handler := httpapi.New(
		*namespaceFlag,
		*prometheusURLFlag,
		*bucketNameFlag,
		*photonPrefixFlag,
		*serviceAccountNameFlag,
		*rootDomainFlag,
		*cellNameFlag,
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

	v1.GET("/deployments/:did/instances", handler.InstanceHandler().List)
	v1.GET("/deployments/:did/instances/:iid/shell", handler.InstanceHandler().Shell)
	v1.GET("/deployments/:did/instances/:iid/log", handler.InstanceHandler().Log)

	v1.GET("/deployments/:did/instances/:iid/monitoring/memoryUtil", handler.MonitoringHandler().InstanceMemoryUtil)
	v1.GET("/deployments/:did/instances/:iid/monitoring/memoryUsage", handler.MonitoringHandler().InstanceMemoryUsage)
	v1.GET("/deployments/:did/instances/:iid/monitoring/memoryTotal", handler.MonitoringHandler().InstanceMemoryTotal)
	v1.GET("/deployments/:did/instances/:iid/monitoring/CPUUtil", handler.MonitoringHandler().InstanceCPUUtil)

	v1.GET("/deployments/:did/instances/:iid/monitoring/FastAPIQPS", handler.MonitoringHandler().InstanceFastAPIQPS)
	v1.GET("/deployments/:did/instances/:iid/monitoring/FastAPILatency", handler.MonitoringHandler().InstanceFastAPILatency)
	v1.GET("/deployments/:did/instances/:iid/monitoring/FastAPIByPathQPS", handler.MonitoringHandler().InstanceFastAPIQPSByPath)
	v1.GET("/deployments/:did/instances/:iid/monitoring/FastAPIByPathLatency", handler.MonitoringHandler().InstanceFastAPILatencyByPath)

	v1.GET("/deployments/:did/instances/:iid/monitoring/GPUMemoryUtil", handler.MonitoringHandler().InstanceGPUMemoryUtil)
	v1.GET("/deployments/:did/instances/:iid/monitoring/GPUMemoryUsage", handler.MonitoringHandler().InstanceGPUMemoryUsage)
	v1.GET("/deployments/:did/instances/:iid/monitoring/GPUMemoryTotal", handler.MonitoringHandler().InstanceGPUMemoryTotal)
	v1.GET("/deployments/:did/instances/:iid/monitoring/GPUUtil", handler.MonitoringHandler().InstanceGPUUtil)

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
		// TODO: create this table in mothership
		// TODO: clean up this table in mothership
		kv, err := kv.NewKVDynamoDB(*clusterNameFlag + "-tuna")
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

	router.Run(fmt.Sprintf(":%d", apiServerPort))
}

func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Origin", "https://dashboard.lepton.ai")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, PUT, HEAD, PATCH, GET, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization, Deployment")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
