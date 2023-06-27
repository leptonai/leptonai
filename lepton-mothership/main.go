package main

import (
	"github.com/leptonai/lepton/lepton-mothership/cluster"
	"github.com/leptonai/lepton/lepton-mothership/httpapi"
	"github.com/leptonai/lepton/lepton-mothership/terraform"
	"github.com/leptonai/lepton/lepton-mothership/workspace"

	"github.com/gin-gonic/gin"
	_ "gocloud.dev/blob/s3blob"
)

func main() {
	terraform.MustInit()

	cluster.Init()
	workspace.Init()

	router := gin.Default()
	api := router.Group("/api")
	v1 := api.Group("/v1")

	v1.GET("/clusters", httpapi.HandleClusterList)
	v1.POST("/clusters", httpapi.HandleClusterCreate)
	v1.GET("/clusters/:clname", httpapi.HandleClusterGet)
	v1.GET("/clusters/:clname/logs", httpapi.HandleClusterGetLogs)
	v1.PATCH("/clusters", httpapi.HandleClusterUpdate)
	v1.DELETE("/clusters/:clname", httpapi.HandleClusterDelete)

	v1.GET("/workspaces", httpapi.HandleWorkspaceList)
	v1.POST("/workspaces", httpapi.HandleWorkspaceCreate)
	v1.GET("/workspaces/:wsname", httpapi.HandleWorkspaceGet)
	v1.GET("/workspaces/:wsname/logs", httpapi.HandleWorkspaceGetLogs)
	v1.PATCH("/workspaces", httpapi.HandleWorkspaceUpdate)
	v1.DELETE("/workspaces/:wsname", httpapi.HandleWorkspaceDelete)

	v1.GET("/users", httpapi.HandleUserList)
	v1.POST("/users", httpapi.HandleUserCreate)
	v1.GET("/users/:uname", httpapi.HandleUserGet)
	v1.DELETE("/users/:uname", httpapi.HandleUserDelete)

	router.Run(":15213")
}
