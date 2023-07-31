package httpapi

import (
	"os"
	"testing"

	"github.com/leptonai/lepton/api-server/httpapi"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

const (
	mountPath = "/tmp/lepton-test"
)

var (
	h  httpapi.Handler
	r  *gin.Engine
	v1 *gin.RouterGroup
)

func TestMain(m *testing.M) {
	r, v1 = SetUpStorageTest()
	code := m.Run()
	os.Exit(code)
}

func SetUpStorageTest() (*gin.Engine, *gin.RouterGroup) {
	router := gin.Default()
	router.Use(requestid.New())
	api := router.Group("/api")
	v1 := api.Group("/v1")

	sh := httpapi.NewStorageHandler(h, mountPath)
	v1.GET("/storage/default/*path", sh.GetFileOrDir)
	v1.POST("/storage/default/*path", sh.CreateFile)
	v1.PUT("/storage/default/*path", sh.CreateDir)
	v1.DELETE("/storage/default/*path", sh.DeleteFileOrDir)
	v1.HEAD("/storage/default/*path", sh.CheckExists)
	return router, v1
}
