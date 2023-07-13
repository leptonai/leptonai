package main

import (
	"context"
	"net/http"
	"time"

	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-mothership/cluster"
	"github.com/leptonai/lepton/lepton-mothership/httpapi"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
	"github.com/leptonai/lepton/lepton-mothership/workspace"

	ginzap "github.com/gin-contrib/zap"
	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	_ "gocloud.dev/blob/s3blob"
)

func main() {
	terraform.MustInit()

	cluster.Init()
	workspace.Init()

	router := gin.Default()

	logger := goutil.Logger.Desugar()
	// Add a ginzap middleware, which:
	//   - Logs all requests, like a combined access and error log.
	//   - Logs to stdout.
	//   - RFC3339 with UTC time format.
	router.Use(ginzap.Ginzap(logger, time.RFC3339, true))

	// Logs all panic to error log
	//   - stack means whether output the stack info.
	router.Use(ginzap.RecoveryWithZap(logger, true))

	router.GET("/metrics", gin.WrapH(promhttp.Handler()))

	api := router.Group("/api")
	v1 := api.Group("/v1")

	v1.GET("/clusters", httpapi.HandleClusterList)
	v1.POST("/clusters", httpapi.HandleClusterCreate)
	v1.GET("/clusters/:clname", httpapi.HandleClusterGet)
	v1.GET("/clusters/:clname/logs", httpapi.HandleClusterGetLogs)
	v1.GET("/clusters/:clname/failure", httpapi.HandleClusterGetFailureLog)
	v1.PATCH("/clusters", httpapi.HandleClusterUpdate)
	v1.DELETE("/clusters/:clname", httpapi.HandleClusterDelete)

	v1.GET("/workspaces", httpapi.HandleWorkspaceList)
	v1.POST("/workspaces", httpapi.HandleWorkspaceCreate)
	v1.GET("/workspaces/:wsname", httpapi.HandleWorkspaceGet)
	v1.GET("/workspaces/:wsname/logs", httpapi.HandleWorkspaceGetLogs)
	v1.GET("//workspaces/:wsname/failure", httpapi.HandleWorkspaceGetFailureLog)
	v1.PATCH("/workspaces", httpapi.HandleWorkspaceUpdate)
	v1.DELETE("/workspaces/:wsname", httpapi.HandleWorkspaceDelete)

	v1.GET("/users", httpapi.HandleUserList)
	v1.POST("/users", httpapi.HandleUserCreate)
	v1.GET("/users/:uname", httpapi.HandleUserGet)
	v1.DELETE("/users/:uname", httpapi.HandleUserDelete)

	server := &http.Server{
		Addr:    ":15213",
		Handler: router,
	}
	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			goutil.Logger.Fatalw("failed to listen and serve",
				"error", err,
			)
		}
	}()

	// quit every 24 hours to pull new image
	time.Sleep(time.Hour * 24)
	for { // wait until no jobs are running
		cluster.Worker.Lock()
		workspace.Worker.Lock()
		if workspace.Worker.CountJobs() == 0 && cluster.Worker.CountJobs() == 0 {
			// Do not release locks to prevent new jobs from being created
			break
		}
		workspace.Worker.Unlock()
		cluster.Worker.Unlock()
		time.Sleep(time.Minute)
	}
	// gracefully shutdown server
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := server.Shutdown(ctx); err != nil {
		goutil.Logger.Fatalw("failed to shutting down server",
			"error", err,
		)
	}

	goutil.Logger.Infow("server exiting")
}
