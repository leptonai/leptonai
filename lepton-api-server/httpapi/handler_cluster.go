package httpapi

import (
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/leptonai/lepton/lepton-api-server/util"
	"github.com/leptonai/lepton/lepton-api-server/version"
)

type ClusterInfo struct {
	sync.Mutex

	version.Info `json:",inline"`

	ClusterName string `json:"cluster_name"`
	// SupportedAccelerators is a map from accelerator type to max number of accelerators a node can have.
	SupportedAccelerators map[string]int `json:"supported_accelerators"`
	// MaxGenericComputeSize is the largest generic compute size in the cluster.
	MaxGenericComputeSize *util.MaxAllocatableSize `json:"max_generic_compute_size"`
}

func (ci *ClusterInfo) UpdateSupportedAccelerators(a map[string]int) {
	ci.Lock()
	defer ci.Unlock()

	ci.SupportedAccelerators = a
}

func (ci *ClusterInfo) UpdateMaxAllocatableSize(m *util.MaxAllocatableSize) {
	ci.Lock()
	defer ci.Unlock()

	ci.MaxGenericComputeSize = m
}

type ClusterInfoHandler struct {
	ClusterInfo *ClusterInfo
}

func NewClusterInfoHandler(clusterName string) *ClusterInfoHandler {
	cih := &ClusterInfoHandler{
		ClusterInfo: &ClusterInfo{
			Info:        version.VersionInfo,
			ClusterName: clusterName,
		},
	}

	go cih.run()

	return cih
}

func (ci *ClusterInfoHandler) Handle(c *gin.Context) {
	ci.ClusterInfo.Lock()
	defer ci.ClusterInfo.Unlock()

	c.JSON(http.StatusOK, ci.ClusterInfo)
}

func (ci *ClusterInfoHandler) run() {
	go ci.updateAcceleratorsPeriodically()
	ci.updateMaxAllocatableSizePeriodically()
}

func (ci *ClusterInfoHandler) updateAcceleratorsPeriodically() {
	// fast update at the beginning
	ci.updateAccelerators()

	ticker := time.NewTicker(time.Minute)

	for range ticker.C {
		ci.updateAccelerators()
	}
}

func (ci *ClusterInfoHandler) updateAccelerators() {
	acc, err := util.GetAccelerators()
	if err != nil {
		log.Printf("Error retrieving accelerators: %v", err)
	} else {
		ci.ClusterInfo.UpdateSupportedAccelerators(acc)
	}
}

func (ci *ClusterInfoHandler) updateMaxAllocatableSizePeriodically() {
	// fast update at the beginning
	ci.updateMaxAllocatableSize()

	ticker := time.NewTicker(time.Minute)

	for range ticker.C {
		ci.updateMaxAllocatableSize()
	}
}

func (ci *ClusterInfoHandler) updateMaxAllocatableSize() {
	m, err := util.GetMaxAllocatableSize()
	if err != nil {
		log.Printf("Error retrieving max allocatable size: %v", err)
	} else {
		ci.ClusterInfo.UpdateMaxAllocatableSize(m)
	}
}
