package httpapi

import (
	"net/http"
	"time"

	"github.com/leptonai/lepton/go-pkg/version"

	"github.com/gin-gonic/gin"
)

type Info struct {
	version.Info `json:",inline"`
	StartTime    time.Time `json:"start_time"`
}

type InfoHandler struct {
	Info *Info
}

func NewInfoHandler() *InfoHandler {
	return &InfoHandler{
		Info: &Info{
			Info:      version.VersionInfo,
			StartTime: time.Now(),
		},
	}
}

func (ih *InfoHandler) HandleGet(c *gin.Context) {
	c.JSON(http.StatusOK, ih.Info)
}
