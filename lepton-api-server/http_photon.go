package main

import (
	"context"
	"io"
	"net/http"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

func photonDownloadHandler(c *gin.Context) {
	pid := c.Param("pid")
	ph := photonDB.GetByID(pid)
	if ph == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "photon " + pid + " does not exist."})
		return
	}
	body, err := photonBucket.ReadAll(context.Background(), ph.GetUniqName())
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to get photon " + pid + " from S3: " + err.Error()})
		return
	}
	c.Data(http.StatusOK, "application/zip", body)
}

func photonGetHandler(c *gin.Context) {
	content := c.DefaultQuery("content", "false")
	if content == "true" { // download the file from S3 and return
		photonDownloadHandler(c)
	} else {
		pid := c.Param("pid")
		metadata := photonDB.GetByID(pid)
		if metadata == nil {
			c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "photon " + pid + " does not exist."})
			return
		}
		c.JSON(http.StatusOK, httpapi.NewPhoton(metadata).Output())
	}
}

func photonDeleteHandler(c *gin.Context) {
	pid := c.Param("pid")
	ph := photonDB.GetByID(pid)
	if ph == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "photon " + pid + " does not exist."})
		return
	}
	err := photonBucket.Delete(context.Background(), ph.GetUniqName())
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to delete photon " + pid + " from S3: " + err.Error()})
		return
	}

	err = DeletePhotonCR(ph)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to delete photon " + pid + " crd: " + err.Error()})
		return
	}

	photonDB.Delete(ph)
	c.Status(http.StatusOK)
}

func photonListHandler(c *gin.Context) {
	name := c.DefaultQuery("name", "")
	var phs []*leptonaiv1alpha1.Photon
	if name == "" {
		phs = photonDB.GetAll()
	} else {
		phs = photonDB.GetByName(name)
	}
	phsMetadata := make([]*httpapi.Photon, 0, len(phs))
	for _, ph := range phs {
		phsMetadata = append(phsMetadata, httpapi.NewPhoton(ph).Output())
	}
	c.JSON(http.StatusOK, phsMetadata)
}

func photonPostHandler(c *gin.Context) {
	// Open the zip archive
	// TODO: improve the performance by using io.Pipe
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	ph, err := getPhotonFromMetadata(body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "failed to get photon metadata: " + err.Error()})
		return
	}

	err = CreatePhotonCR(ph)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create photon CR: " + err.Error()})
		return
	}

	// TODO: failure recovery: if the server crashes here, we should be able to delete the object uploaded to S3

	// Upload to S3
	// TODO: append the content hash to the s3 key as suffix
	err = photonBucket.WriteAll(context.TODO(), ph.GetUniqName(), body, nil)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to upload photon to S3: " + err.Error()})
		return
	}

	cr, err := ReadPhotonCR(ph.GetUniqName())
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create photon CR: " + err.Error()})
		return
	}

	photonDB.Add(cr)

	c.JSON(http.StatusOK, httpapi.NewPhoton(ph).Output())
}
