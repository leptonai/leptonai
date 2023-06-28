package httpapi

import (
	"net/http"

	gcssyncer "github.com/leptonai/lepton/storage-syncer/gcs-syncer"

	"github.com/gin-gonic/gin"
	"github.com/leptonai/lepton/go-pkg/httperrors"
)

type StorageSyncerHandler struct {
	Handler
}

// Create creates a storage syncer.
func (h *StorageSyncerHandler) Create(c *gin.Context) {
	s := StorageSyncer{}
	err := c.Bind(&s)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to parse input: " + err.Error()})
		return
	}

	err = gcssyncer.CreateSyncerForDefaultEFS(h.namespace, s.Metadata.Name, s.Spec.GCSURL, s.Spec.DestPath, s.Spec.CredJSON)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create storage syncer: " + err.Error()})
		return
	}
	c.Status(http.StatusCreated)
}

// Delete deletes a storage syncer.
func (h *StorageSyncerHandler) Delete(c *gin.Context) {
	name := c.Param("name")
	err := gcssyncer.DeleteSyncerForDefaultEFS(h.namespace, name)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete storage syncer: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}

// List lists all storage syncers.
func (h *StorageSyncerHandler) List(c *gin.Context) {
	// TODO
	c.Status(http.StatusOK)
}
