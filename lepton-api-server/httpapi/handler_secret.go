package httpapi

import (
	"context"
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
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to parse input: " + err.Error()})
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
	key := c.Param("key")

	// check if the secret is used by any deployments
	// TODO: this has data race: if users create a deployment after this check
	// but before the actual deletion of the secret from DB, then the deployment
	// will be created with a secret that is being deleted.
	list, err := h.ldDB.List(context.Background())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to verify whether or not the secret is in use: " + err.Error()})
		return
	}
	for _, ld := range list {
		for _, env := range ld.Spec.Envs {
			if env.ValueFrom.SecretNameRef == key {
				c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeValidationError, "message": "secret " + key + " is in use: deployment " + ld.GetSpecName()})
				return
			}
		}
	}

	if err := h.secretDB.Delete(key); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete secret: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}
