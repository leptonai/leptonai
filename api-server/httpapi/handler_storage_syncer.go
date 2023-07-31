package httpapi

import (
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	gcssyncer "github.com/leptonai/lepton/storage-syncer/gcs-syncer"

	"github.com/gin-gonic/gin"
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

	err = gcssyncer.CreateSyncerForDefaultEFS(c, h.namespace, s.Metadata.Name, s.Spec.GCSURL, s.Spec.DestPath, s.Spec.CredJSON)
	if err != nil {
		goutil.Logger.Errorw("failed to create storage syncer",
			"operation", "createStorageSyncer",
			"storageSyncer", s.Metadata.Name,
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create storage syncer: " + err.Error()})
		return
	}

	goutil.Logger.Infow("created storage syncer",
		"operation", "createStorageSyncer",
		"storageSyncer", s.Metadata.Name,
	)

	c.Status(http.StatusCreated)
}

// Delete deletes a storage syncer.
func (h *StorageSyncerHandler) Delete(c *gin.Context) {
	name := c.Param("name")
	err := gcssyncer.DeleteSyncerForDefaultEFS(c, h.namespace, name)
	if err != nil {
		goutil.Logger.Errorw("failed to delete storage syncer",
			"operation", "deleteStorageSyncer",
			"storageSyncer", name,
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete storage syncer: " + err.Error()})
		return
	}

	goutil.Logger.Infow("deleted storage syncer",
		"operation", "deleteStorageSyncer",
		"storageSyncer", name,
	)

	c.Status(http.StatusOK)
}

// List lists all storage syncers.
func (h *StorageSyncerHandler) List(c *gin.Context) {
	// TODO
	c.Status(http.StatusOK)
}
