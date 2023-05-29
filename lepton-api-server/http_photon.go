package main

import (
	"context"
	"io"
	"net/http"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"

	"github.com/gin-gonic/gin"
)

func photonDownloadHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	metadata := photonDB.GetByID(uuid)
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "photon " + uuid + " does not exist."})
		return
	}
	body, err := photonBucket.ReadAll(context.Background(), util.JoinByDash(metadata.Name, uuid))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to get photon " + uuid + " from S3: " + err.Error()})
		return
	}
	c.Data(http.StatusOK, "application/zip", body)
}

func photonGetHandler(c *gin.Context) {
	content := c.DefaultQuery("content", "false")
	if content == "true" { // download the file from S3 and return
		photonDownloadHandler(c)
	} else {
		uuid := c.Param("uuid")
		metadata := photonDB.GetByID(uuid)
		if metadata == nil {
			c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "photon " + uuid + " does not exist."})
			return
		}
		c.JSON(http.StatusOK, metadata)
	}
}

func photonDeleteHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	metadata := photonDB.GetByID(uuid)
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "photon " + uuid + " does not exist."})
		return
	}
	err := photonBucket.Delete(context.Background(), util.JoinByDash(metadata.Name, uuid))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to delete photon " + uuid + " from S3: " + err.Error()})
		return
	}

	err = DeletePhotonCR(metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to delete photon " + uuid + " crd: " + err.Error()})
		return
	}

	photonDB.Delete(metadata)
	c.Status(http.StatusOK)
}

func photonListHandler(c *gin.Context) {
	name := c.DefaultQuery("name", "")
	if name == "" {
		c.JSON(http.StatusOK, photonDB.GetAll())
	} else {
		c.JSON(http.StatusOK, photonDB.GetByName(name))
	}
}

func photonPostHandler(c *gin.Context) {
	// Open the zip archive
	// TODO: improve the performance by using io.Pipe
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	uuid := util.HexHash(body)

	ph, err := getPhotonFromMetadata(body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "failed to get photon metadata: " + err.Error()})
		return
	}

	ph.ID = uuid
	now := time.Now()
	ph.CreatedAt = now.UnixMilli()

	err = CreatePhotonCR(ph)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to create photon CR: " + err.Error()})
		return
	}

	// TODO: failure recovery: if the server crashes here, we should be able to delete the object uploaded to S3

	// Upload to S3
	// TODO: append the content hash to the s3 key as suffix
	err = photonBucket.WriteAll(context.TODO(), util.JoinByDash(ph.Name, uuid), body, nil)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to upload photon to S3: " + err.Error()})
		return
	}

	photonDB.Add(ph)
	c.JSON(http.StatusOK, ph)
}
