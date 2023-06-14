package httpapi

import (
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s/secret"

	"github.com/gin-gonic/gin"
)

type SecretHandler struct {
	Handler
}

func (h *SecretHandler) List(c *gin.Context) {
	keys, err := h.secretDB.List()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list secret: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, keys)
}

func (h *SecretHandler) Create(c *gin.Context) {
	secrets := []secret.SecretItem{}
	if err := c.BindJSON(&secrets); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to parse input: " + err.Error()})
		return
	}
	err := h.secretDB.Put(secrets)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create secret: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}

func (h *SecretHandler) Delete(c *gin.Context) {
	err := h.secretDB.Delete(c.Param("key"))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete secret: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}
