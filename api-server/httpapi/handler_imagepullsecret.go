package httpapi

import (
	"net/http"
	"strings"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s/secret"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"github.com/gin-gonic/gin"
)

// ImagePullSecret is a secret for pulling images from private registry.
type ImagePullSecret struct {
	Metadata Metadata            `json:"metadata"`
	Spec     ImagePullSecretSpec `json:"spec"`
}

// ImagePullSecretSpec is the spec of ImagePullSecret.
type ImagePullSecretSpec struct {
	// Private registry FQDN. Use https://index.docker.io/v1/ for DockerHub.
	RegistryServer string `json:"registry_server"`
	// Username for the private private registry.
	Username string `json:"username"`
	// Password for the private registry.
	Password string `json:"password"`
	// email for the private registry.
	Email string `json:"email"`
}

// ImagePullSecretHandler handles image pull secrets.
type ImagePullSecretHandler struct {
	Handler
}

// AddToRoute adds routes to the gin engine.
func (h *ImagePullSecretHandler) AddToRoute(r gin.IRoutes) {
	r.GET("/imagepullsecrets", h.List)
	r.POST("/imagepullsecrets", h.Create)
	r.DELETE("/imagepullsecrets/:ssname", h.Delete)
}

// List lists all names of the image pull secrets
func (h *ImagePullSecretHandler) List(c *gin.Context) {
	ss, err := secret.ListAllSecretSets(c, h.namespace)
	if err != nil {
		goutil.Logger.Errorw("failed to list image pull secrets",
			"operation", "ListImagePullSecrets",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list image pull secrets: " + err.Error()})
		return
	}

	iss := []ImagePullSecret{}
	for _, s := range ss {
		if !strings.HasPrefix(s, secret.ImagePullSecretPrefix) {
			continue
		}

		iss = append(iss, ImagePullSecret{
			Metadata: Metadata{
				Name: s[len(secret.ImagePullSecretPrefix):],
			},
		})
	}

	c.JSON(http.StatusOK, iss)
}

// CreateOrUpdate creates an image pull secret
func (h *ImagePullSecretHandler) Create(c *gin.Context) {
	ip := ImagePullSecret{}
	err := c.BindJSON(&ip)
	if err != nil {
		goutil.Logger.Debugw("failed to parse input",
			"operation", "CreateImagePullSecret",
			"error", err,
		)

		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to parse input: " + err.Error()})
		return
	}

	s := secret.New(h.namespace, secret.ImagePullSecretPrefix+ip.Metadata.Name, nil)

	items, err := s.List(c)
	if err != nil {
		goutil.Logger.Errorw("failed to check pull image secret",
			"operation", "CreateImagePullSecret",
			"secret", ip.Metadata.Name,
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to check pull image secret: " + err.Error()})
		return
	}
	if len(items) > 0 {
		goutil.Logger.Debugw("pull image secret already exists",
			"operation", "CreateImagePullSecret",
			"secret", ip.Metadata.Name,
		)

		c.JSON(http.StatusConflict, gin.H{"code": httperrors.ErrorCodeResourceConflict, "message": "pull image secret already exists"})
		return
	}

	// TODO: add lock to avoid race condition on concurrent creation
	err = s.PutPrivateRegistry(c, ip.Spec.RegistryServer, ip.Spec.Username, ip.Spec.Password, ip.Spec.Email)
	if err != nil {
		goutil.Logger.Errorw("failed to create secret",
			"operation", "CreateImagePullSecret",
			"secret", ip.Metadata.Name,
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create secret: " + err.Error()})
		return
	}

	c.Status(http.StatusCreated)
}

// Delete deletes an image pull secret
func (h *ImagePullSecretHandler) Delete(c *gin.Context) {
	ssname := c.Param("ssname")

	err := secret.New(h.namespace, secret.ImagePullSecretPrefix+ssname, nil).Destroy(c)
	if err != nil {
		goutil.Logger.Errorw("failed to delete secret",
			"operation", "DeleteImagePullSecret",
			"secret", ssname,
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete secret: " + err.Error()})
		return
	}

	c.Status(http.StatusOK)
}
