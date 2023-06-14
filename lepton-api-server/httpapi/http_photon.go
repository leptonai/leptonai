package httpapi

import (
	"context"
	"io"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

type PhotonHandler struct {
	Handler
}

func (h *PhotonHandler) Download(c *gin.Context) {
	pid := c.Param("pid")
	ph := h.photonDB.GetByID(pid)
	if ph == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "photon " + pid + " does not exist."})
		return
	}
	body, err := h.photonBucket.ReadAll(context.Background(), ph.GetSpecUniqName())
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get photon " + pid + " from S3: " + err.Error()})
		return
	}
	c.Data(http.StatusOK, "application/zip", body)
}

func (h *PhotonHandler) Get(c *gin.Context) {
	content := c.DefaultQuery("content", "false")
	if content == "true" { // download the file from S3 and return
		h.Download(c)
	} else {
		pid := c.Param("pid")
		ph := h.photonDB.GetByID(pid)
		if ph == nil {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "photon " + pid + " does not exist."})
			return
		}
		c.JSON(http.StatusOK, NewPhoton(ph).Output())
	}
}

func (h *PhotonHandler) Delete(c *gin.Context) {
	pid := c.Param("pid")

	// check if the photon is used by any deployments
	// TODO: this has data race: if users create a deployment after this check
	// but before the actual deletion of the photon from DB, then the deployment
	// will be created with a photon that is being deleted.
	for _, ld := range h.deploymentDB.GetAll() {
		if ld.Spec.PhotonID == pid {
			c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "photon " + pid + " is used by deployment " + ld.Name})
			return
		}
	}

	ph := h.photonDB.GetByID(pid)
	if ph == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "photon " + pid + " does not exist."})
		return
	}
	if err := k8s.Client.Delete(context.Background(), ph); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete photon " + pid + " crd: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}

func (h *PhotonHandler) List(c *gin.Context) {
	name := c.DefaultQuery("name", "")
	var phs []*leptonaiv1alpha1.Photon
	if name == "" {
		phs = h.photonDB.GetAll()
	} else {
		phs = h.photonDB.GetByName(name)
	}
	ret := make([]*Photon, 0, len(phs))
	for _, ph := range phs {
		ret = append(ret, NewPhoton(ph).Output())
	}
	c.JSON(http.StatusOK, ret)
}

func (h *PhotonHandler) Create(c *gin.Context) {
	// Open the zip archive
	body, err := getContentFromFileOrRawBody(c.Request)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to read request body: " + err.Error()})
		return
	}

	ph, err := h.getPhotonFromMetadata(body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to get photon metadata: " + err.Error()})
		return
	}

	if h.photonDB.GetByID(ph.GetSpecID()) != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "photon " + ph.GetSpecID() + " already exists."})
		return
	}

	// Upload to S3
	// TODO: append the content hash to the s3 key as suffix
	err = h.photonBucket.WriteAll(context.Background(), ph.GetSpecUniqName(), body, nil)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to upload photon to S3: " + err.Error()})
		return
	}

	// TODO: failure recovery: if the server crashes here, we should be able to delete the object uploaded to S3
	err = k8s.Client.Create(context.Background(), ph)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create photon CR: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, NewPhoton(ph).Output())
}

func getContentFromFileOrRawBody(r *http.Request) ([]byte, error) {
	// TODO: improve the performance by using io.Pipe
	file, _, err := r.FormFile("file")
	if err != nil {
		return io.ReadAll(r.Body)
	}
	defer file.Close()

	body, err := io.ReadAll(file)
	if err != nil {
		return io.ReadAll(r.Body)
	}
	return body, nil
}
