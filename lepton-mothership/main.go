package main

import (
	"time"

	"github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-mothership/cluster"
	"github.com/leptonai/lepton/lepton-mothership/httpapi"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
	"github.com/leptonai/lepton/lepton-mothership/workspace"

	ginzap "github.com/gin-contrib/zap"
	"github.com/gin-gonic/gin"
	_ "gocloud.dev/blob/s3blob"
)

func main() {
	terraform.MustInit()

	cluster.Init()
	workspace.Init()

	router := gin.Default()

	logger := util.Logger.Desugar()
	// Add a ginzap middleware, which:
	//   - Logs all requests, like a combined access and error log.
	//   - Logs to stdout.
	//   - RFC3339 with UTC time format.
	router.Use(ginzap.Ginzap(logger, time.RFC3339, true))

	// Logs all panic to error log
	//   - stack means whether output the stack info.
	router.Use(ginzap.RecoveryWithZap(logger, true))

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

	router.Run(":15213")
}
