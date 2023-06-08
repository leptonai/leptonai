package main

import (
	"github.com/leptonai/lepton/lepton-mothership/httpapi"
	"github.com/leptonai/lepton/lepton-mothership/terraform"

	"github.com/gin-gonic/gin"
	_ "gocloud.dev/blob/s3blob"
)

func main() {
	terraform.MustInit()

	router := gin.Default()
	api := router.Group("/api")
	v1 := api.Group("/v1")

	v1.GET("/clusters", httpapi.HandleClusterList)
	v1.POST("/clusters", httpapi.HandleClusterCreate)
	v1.GET("/clusters/:clname", httpapi.HandleClusterGet)
	v1.PATCH("/clusters/:clname", httpapi.HandleClusterUpdate)
	v1.DELETE("/clusters/:clname", httpapi.HandleClusterDelete)

	v1.GET("/cells", httpapi.HandleCellList)
	v1.POST("/cells", httpapi.HandleCellCreate)
	v1.GET("/cells/:ceame", httpapi.HandleCellGet)
	v1.PATCH("/cells/:ceame", httpapi.HandleCellUpdate)
	v1.DELETE("/cells/:ceame", httpapi.HandleCellDelete)

	v1.GET("/users", httpapi.HandleUserList)
	v1.POST("/users", httpapi.HandleUserCreate)
	v1.DELETE("/users/:uname", httpapi.HandleUserGet)
	v1.DELETE("/users/:uname", httpapi.HandleUserDelete)
}
