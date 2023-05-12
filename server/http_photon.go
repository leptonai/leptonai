package main

import (
	"context"
	"io"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

func photonDownloadHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	photonMapRWLock.RLock()
	metadata := photonById[uuid]
	photonMapRWLock.RUnlock()
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "photon " + uuid + " does not exist."})
		return
	}
	body, err := photonBucket.ReadAll(context.Background(), joinNameByDash(metadata.Name, uuid))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to get photon " + uuid + " from S3: " + err.Error()})
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
		photonMapRWLock.RLock()
		metadata := photonById[uuid]
		photonMapRWLock.RUnlock()
		if metadata == nil {
			c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "photon " + uuid + " does not exist."})
			return
		}
		c.JSON(http.StatusOK, metadata)
	}
}

func photonDeleteHandler(c *gin.Context) {
	uuid := c.Param("uuid")
	photonMapRWLock.RLock()
	metadata := photonById[uuid]
	photonMapRWLock.RUnlock()
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "photon " + uuid + " does not exist."})
		return
	}
	err := photonBucket.Delete(context.Background(), joinNameByDash(metadata.Name, uuid))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to delete photon " + uuid + " from S3: " + err.Error()})
		return
	}

	err = DeletePhotonCR(metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to delete photon " + uuid + " crd: " + err.Error()})
		return
	}

	photonMapRWLock.Lock()
	delete(photonById, uuid)
	delete(photonByName[metadata.Name], uuid)
	photonMapRWLock.Unlock()

	c.Status(http.StatusOK)
}

func photonListHandler(c *gin.Context) {
	name := c.DefaultQuery("name", "")
	// TODO: have a well organized json return value
	ret := make([]*Photon, 0)

	photonMapRWLock.RLock()
	retList := photonById
	if name != "" {
		retList = photonByName[name]
	}
	for _, metadata := range retList {
		ret = append(ret, metadata)
	}
	photonMapRWLock.RUnlock()

	c.JSON(http.StatusOK, ret)
}

func photonPostHandler(c *gin.Context) {
	// Open the zip archive
	// TODO: improve the performance by using io.Pipe
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	uuid := hash(body)

	metadata, err := getPhotonFromMetadata(body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "failed to get photon metadata: " + err.Error()})
		return
	}

	metadata.ID = uuid
	now := time.Now()
	metadata.CreatedAt = now.UnixMilli()

	err = CreatePhotonCR(metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to create photon CR: " + err.Error()})
		return
	}

	// TODO: failure recovery: if the server crashes here, we should be able to delete the object uploaded to S3

	// Upload to S3
	// TODO: append the content hash to the s3 key as suffix
	err = photonBucket.WriteAll(context.TODO(), joinNameByDash(metadata.Name, uuid), body, nil)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to upload photon to S3: " + err.Error()})
		return
	}

	photonMapRWLock.Lock()
	photonById[uuid] = metadata
	if photonByName[metadata.Name] == nil {
		photonByName[metadata.Name] = make(map[string]*Photon)
	}
	photonByName[metadata.Name][uuid] = metadata
	photonMapRWLock.Unlock()

	c.JSON(http.StatusOK, metadata)
}
