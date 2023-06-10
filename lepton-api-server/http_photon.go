package main

import (
	"context"
	"io"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

func photonDownloadHandler(c *gin.Context) {
	pid := c.Param("pid")
	ph := photonDB.GetByID(pid)
	if ph == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "photon " + pid + " does not exist."})
		return
	}
	body, err := photonBucket.ReadAll(context.Background(), ph.GetSpecUniqName())
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get photon " + pid + " from S3: " + err.Error()})
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
		ph := photonDB.GetByID(pid)
		if ph == nil {
			c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "photon " + pid + " does not exist."})
			return
		}
		c.JSON(http.StatusOK, httpapi.NewPhoton(ph).Output())
	}
}

func photonDeleteHandler(c *gin.Context) {
	pid := c.Param("pid")
	ph := photonDB.GetByID(pid)
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

func photonListHandler(c *gin.Context) {
	name := c.DefaultQuery("name", "")
	var phs []*leptonaiv1alpha1.Photon
	if name == "" {
		phs = photonDB.GetAll()
	} else {
		phs = photonDB.GetByName(name)
	}
	ret := make([]*httpapi.Photon, 0, len(phs))
	for _, ph := range phs {
		ret = append(ret, httpapi.NewPhoton(ph).Output())
	}
	c.JSON(http.StatusOK, ret)
}

func photonPostHandler(c *gin.Context) {
	// Open the zip archive
	// TODO: improve the performance by using io.Pipe
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	ph, err := getPhotonFromMetadata(body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to get photon metadata: " + err.Error()})
		return
	}

	// Upload to S3
	// TODO: append the content hash to the s3 key as suffix
	err = photonBucket.WriteAll(context.Background(), ph.GetSpecUniqName(), body, nil)
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

	c.JSON(http.StatusOK, httpapi.NewPhoton(ph).Output())
}
