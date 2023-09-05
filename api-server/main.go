package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/leptonai/lepton/api-server/httpapi"
	"github.com/leptonai/lepton/api-server/util"
	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/metering"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/go-pkg/version"
	"github.com/leptonai/lepton/metrics"

	"github.com/gin-contrib/requestid"
	ginzap "github.com/gin-contrib/zap"
	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	_ "go.uber.org/automaxprocs"
	_ "gocloud.dev/blob/s3blob"
)

const (
	apiServerPort = 20863
	apiServerPath = "/api/"
	rootPath      = "/"
)

func main() {
	clusterNameFlag := flag.String("cluster-name", "", "name of the Kubernetes cluster this server is running on")
	workspaceNameFlag := flag.String("workspace-name", "default", "workspace name")
	namespaceFlag := flag.String("namespace", "default", "namespace to create resources")
	stateFlag := flag.String("state", "normal", "workspace state after starting the server (allowed values: normal, paused, terminated)")

	s3ReadOnlyAccessK8sSecretNameFlag := flag.String("s3-read-only-access-k8s-secret-name", "s3-ro-key", "S3 read only access k8s secret name")
	certificateARNFlag := flag.String("certificate-arn", "", "certificate ARN")
	rootDomainFlag := flag.String("root-domain", "", "root domain")
	sharedALBMainDomainFlag := flag.String("shared-alb-main-domain", "", "main domain for shared alb")

	apiTokenFlag := flag.String("api-token", "", "API token for authentication")
	regionFlag := flag.String("region", "us-east-1", "cluster region")

	bucketTypeFlag := flag.String("bucket-type", "s3", "cloud provider")
	bucketNameFlag := flag.String("bucket-name", "leptonai", "object store bucket name")

	// rename to EFS root handle
	// e.g. fs-12345678:/:fsap-12345678
	efsIDFlag := flag.String("efs-id", "", "EFS ID")

	photonPrefixFlag := flag.String("photon-prefix", "photons", "object store prefix for photon")
	photonImageRegistryFlag := flag.String("photon-image-registry", "605454121064.dkr.ecr.us-east-1.amazonaws.com", "photon image registry")

	dynamodbNameFlag := flag.String("dynamodb-name", "", "dynamodb table name")
	prometheusURLFlag := flag.String("prometheus-url", "http://kube-prometheus-stack-prometheus.kube-prometheus-stack.svc.cluster.local:9090", "prometheus URL")
	enableTunaFlag := flag.Bool("enable-tuna", false, "enable tuna fine-tuning service")

	enableStorageFlag := flag.Bool("enable-storage", true, "enable storage service")
	storageMountPathFlag := flag.String("storage-mount-path", "/mnt/efs/default", "mount path for storage service")

	tierFlag := flag.String("tier", "", "tier of the workspace (allowed values: basic, standard, enterprise)")

	requestTimeoutInternal := flag.String("request-timeout", "1m", "HTTP request timeout")

	flag.Parse()

	if args := flag.Args(); len(args) > 0 && args[0] == "version" {
		fmt.Printf("%+v\n", version.VersionInfo)
		os.Exit(0)
	}

	requestTimeoutInternalDur, err := time.ParseDuration(*requestTimeoutInternal)
	if err != nil {
		goutil.Logger.Fatalw("failed to parse request timeout",
			"error", err,
		)
	}

	ctx, cancel := context.WithTimeout(context.Background(), requestTimeoutInternalDur)
	pbu := goutil.MustOpenAndAccessBucket(
		ctx,
		*bucketTypeFlag,
		*bucketNameFlag,
		*regionFlag,
		*photonPrefixFlag,
	)
	backupPrefix := "workspace-backups"
	bbu := goutil.MustOpenAndAccessBucket(
		ctx,
		*bucketTypeFlag,
		*bucketNameFlag,
		*regionFlag,
		backupPrefix,
	)
	cancel()

	workspaceState := httpapi.WorkspaceState(*stateFlag)

	log.Printf("Starting the %s tier Lepton Server on :%d with request timeout %v\n", *tierFlag, apiServerPort, requestTimeoutInternalDur)

	router := gin.Default()
	router.Use(corsMiddleware())
	router.Use(requestid.New())
	router.Use(pauseWorkspaceMiddleware(workspaceState))
	router.Use(timeoutMiddleware(requestTimeoutInternalDur))
	router.Use(metrics.PrometheusMiddlewareForGin("api_server"))

	logger := goutil.Logger.Desugar()
	// Add a ginzap middleware, which:
	//   - Logs all requests, like a combined access and error log.
	//   - Logs to stdout.
	//   - RFC3339 with UTC time format.
	router.Use(ginzap.Ginzap(logger, time.RFC3339, true))

	// Logs all panic to error log
	//   - stack means whether output the stack info.
	router.Use(ginzap.RecoveryWithZap(logger, true))
	router.ContextWithFallback = true

	router.GET("/healthz", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, gin.H{"status": "ok", "version": "v1"})
	})
	router.GET("/metrics", gin.WrapH(promhttp.Handler()))

	api := router.Group("/api")
	v1 := api.Group("/v1")

	handler := httpapi.New(
		*clusterNameFlag,
		*namespaceFlag,
		*prometheusURLFlag,
		*bucketNameFlag,
		*efsIDFlag,
		*photonPrefixFlag,
		*photonImageRegistryFlag,
		*s3ReadOnlyAccessK8sSecretNameFlag,
		*rootDomainFlag,
		*sharedALBMainDomainFlag,
		*workspaceNameFlag,
		*certificateARNFlag,
		*apiTokenFlag,
		pbu,
		bbu,
		workspaceState,
		*tierFlag,
		*storageMountPathFlag,
		*regionFlag,
		*dynamodbNameFlag,
		*enableTunaFlag,
		*enableStorageFlag,
		v1,
	)
	handler.AddToRoute()

	metering.RegisterStorageHandlers()
	// update storage metrics every 60 seconds
	go updateStorageMetrics(60, *storageMountPathFlag, *workspaceNameFlag, *clusterNameFlag, *efsIDFlag)
	router.Run(fmt.Sprintf(":%d", apiServerPort))
}

const (
	dailyOrigin = "https://dashboard.daily.lepton.ai"
)

func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")
		switch origin {
		case dailyOrigin:
			util.SetCORSForDashboard(c.Writer.Header(), dailyOrigin)
		default:
			// https://dashboard.lepton.ai is the default value so we don't need to explicitly set it
			util.SetCORSForDashboard(c.Writer.Header(), "")
		}

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

func pauseWorkspaceMiddleware(workspaceState httpapi.WorkspaceState) gin.HandlerFunc {
	return func(c *gin.Context) {
		if workspaceState != httpapi.WorkspaceStateNormal {
			switch c.Request.Method {
			case http.MethodPut, http.MethodPost, http.MethodPatch:
				c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
					"code":    httperrors.ErrorCodeInvalidRequest,
					"message": "workspace is paused or terminated",
				})
				return
			}
		}
		c.Next()
	}
}

func timeoutMiddleware(t time.Duration) gin.HandlerFunc {
	return func(c *gin.Context) {
		if !strings.HasSuffix(c.Request.URL.Path, "/shell") &&
			!strings.HasSuffix(c.Request.URL.Path, "/log") &&
			!strings.Contains(c.Request.URL.Path, "/storage/") {
			ctx, cancel := context.WithTimeout(c.Request.Context(), t)
			defer cancel()
			c.Request = c.Request.WithContext(ctx)
		}
		c.Next()
	}
}

// exposeStorageMetrics exposes most recent storage metrics
func exposeStorageMetrics(storageMountPath, workspaceName, clusterName, efsID string) {
	sizeWorkspace, err := goutil.TotalDirDiskUsageBytes(storageMountPath)
	if err != nil {
		goutil.Logger.Errorw("failed to get workspace size",
			"operation", "TotalDuDir",
			"workspace", workspaceName,
			"error", err,
		)
		return
	}
	metering.GatherDiskUsage(workspaceName, clusterName, "efs", efsID, int64(sizeWorkspace))
}

// updateStorageMetrics updates storage metrics every secondsDelay seconds
func updateStorageMetrics(secondsDelay int,
	storageMountPath, workspaceName, clusterName, efsID string) {
	timer := time.NewTicker(time.Second * time.Duration(secondsDelay))
	defer timer.Stop()
	for range timer.C {
		exposeStorageMetrics(storageMountPath, workspaceName, clusterName, efsID)
	}
}
