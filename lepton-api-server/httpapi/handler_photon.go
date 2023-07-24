package httpapi

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/datastore"
	"github.com/leptonai/lepton/go-pkg/httperrors"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

type PhotonHandler struct {
	Handler
}

func (h *PhotonHandler) Download(c *gin.Context) {
	pid := c.Param("pid")
	ph, err := h.phDB.Get(c, pid)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "photon " + pid + " not found"})
		return
	}
	body, err := h.photonBucket.ReadAll(c, ph.GetSpecID())
	if err != nil {
		goutil.Logger.Errorw("failed to get photon from object storage",
			"operation", "downloadPhoton",
			"photon", pid,
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get photon " + pid + " from object storage: " + err.Error()})
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
		ph, err := h.phDB.Get(c, pid)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "photon " + pid + " not found"})
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
	list, err := h.ldDB.List(c)
	if err != nil {
		goutil.Logger.Errorw("failed to list deployments",
			"operation", "deletePhoton",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to verify whether or not the photon is in use: " + err.Error()})
		return
	}
	for _, ld := range list {
		if ld.Spec.PhotonID == pid {
			c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeValidationError, "message": "photon " + pid + " is in use: deployment " + ld.GetSpecName()})
			return
		}
	}

	if err := h.phDB.Delete(c, pid); err != nil {
		goutil.Logger.Errorw("failed to delete photon from database",
			"operation", "deletePhoton",
			"photon", pid,
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete photon " + pid + " from database: " + err.Error()})
		return
	}

	goutil.Logger.Infow("photon deleted",
		"operation", "deletePhoton",
		"photon", pid,
	)

	c.Status(http.StatusOK)
}

func (h *PhotonHandler) List(c *gin.Context) {
	name := c.DefaultQuery("name", "")
	var phs []*leptonaiv1alpha1.Photon
	phList, err := h.phDB.List(c)
	if err != nil {
		goutil.Logger.Errorw("failed to list photons",
			"operation", "listPhotons",
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list photons: " + err.Error()})
		return
	}
	if name == "" {
		phs = phList
	} else {
		// TODO efficiency: use a map to index the name
		phs = make([]*leptonaiv1alpha1.Photon, 0)
		for _, ph := range phList {
			if ph.GetSpecName() == name {
				phs = append(phs, ph)
			}
		}
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
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to read request body: " + err.Error()})
		return
	}

	ph, err := h.getPhotonFromMetadata(body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "failed to parse input: " + err.Error()})
		return
	}

	// Upload to S3
	// TODO: append the content hash to the s3 key as suffix
	err = h.photonBucket.WriteAll(c, ph.GetSpecID(), body, nil)
	if err != nil {
		goutil.Logger.Errorw("failed to upload photon to object storage",
			"operation", "createPhoton",
			"photon", ph.GetSpecID(),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to upload photon to object storage: " + err.Error()})
		return
	}

	if err := h.phDB.Create(c, ph.GetSpecID(), ph); err != nil {
		goutil.Logger.Errorw("failed to create photon in database",
			"operation", "createPhoton",
			"photon", ph.GetSpecID(),
			"error", err,
		)
		if datastore.IsErrorAlreadyExist(err) {
			c.JSON(http.StatusConflict, gin.H{"code": httperrors.ErrorCodeResourceConflict, "message": "failed to create photon: " + err.Error()})
		} else {
			c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create photon: " + err.Error()})
		}
		return
	}

	goutil.Logger.Infow("photon created",
		"operation", "createPhoton",
		"photon", ph.GetSpecID(),
	)

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

func (h *PhotonHandler) getPhotonFromMetadata(body []byte) (*leptonaiv1alpha1.Photon, error) {
	reader, err := zip.NewReader(bytes.NewReader(body), int64(len(body)))
	if err != nil {
		return nil, err
	}

	// Find the metadata.json file in the archive
	var metadataFile *zip.File
	for _, file := range reader.File {
		if file.Name == "metadata.json" {
			metadataFile = file
			break
		}
	}
	if metadataFile == nil {
		return nil, fmt.Errorf("metadata.json not found in photon")
	}

	// Read the contents of the metadata.json file
	metadataReader, err := metadataFile.Open()
	if err != nil {
		return nil, err
	}
	defer metadataReader.Close()
	metadataBytes, err := io.ReadAll(metadataReader)
	if err != nil {
		return nil, err
	}

	// Unmarshal the JSON into a Metadata struct
	ph := &leptonaiv1alpha1.Photon{}
	if err := json.Unmarshal(metadataBytes, &ph.Spec); err != nil {
		return nil, err
	}
	if !util.ValidateName(ph.Spec.Name) {
		return nil, fmt.Errorf("invalid name %s: %s", ph.Spec.Name, util.NameInvalidMessage)
	}
	ph.Name = ph.GetSpecName() + "-" + util.HexHash(body)
	ph.Spec.Image = util.UpdateDefaultRegistry(ph.Spec.Image, h.photonImageRegistry)

	return ph, nil
}
