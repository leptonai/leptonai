package main

import (
	"bytes"
	"encoding/json"
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
	body, err := downloadFromS3(bucketName, getPhotonS3ObjectName(metadata.Name, uuid))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to get photon: " + uuid + " from S3"})
		return
	}
	ret, err := io.ReadAll(body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to get photon: " + uuid + " from S3"})
		return
	}
	c.Data(http.StatusOK, "application/zip", ret)
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
			c.JSON(http.StatusNotFound, gin.H{"status": "Failed", "error": "not found", "message": "photon: " + uuid + " not found"})
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
		c.JSON(http.StatusNotFound, gin.H{"status": "Failed", "error": "not found", "message": "photon: " + uuid + " not found"})
		return
	}
	err := deleteS3Object(bucketName, getPhotonS3ObjectName(metadata.Name, uuid))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to delete photon: " + uuid + " from S3"})
		return
	}

	err = DeletePhotonCR(metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to delete photon: " + uuid + " from database"})
		return
	}

	photonMapRWLock.Lock()
	delete(photonById, uuid)
	delete(photonByName[metadata.Name], uuid)
	photonMapRWLock.Unlock()

	c.JSON(http.StatusOK, gin.H{"status": "OK", "message": "deleted " + uuid})
}

func photonListHandler(c *gin.Context) {
	name := c.DefaultQuery("name", "")
	// TODO: have a well organized json return value
	ret := "["
	photonMapRWLock.RLock()
	retList := photonById
	if name != "" {
		retList = photonByName[name]
	}
	for _, metadata := range retList {
		metadataJson, err := json.Marshal(*metadata)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to marshal metadata"})
			photonMapRWLock.RUnlock()
			return
		}
		ret += string(metadataJson) + ","
	}
	photonMapRWLock.RUnlock()
	if ret[len(ret)-1] == ',' {
		ret = ret[:len(ret)-1]
	}
	ret += "]"

	c.String(http.StatusOK, ret)
}

func photonPostHandler(c *gin.Context) {
	// Open the zip archive
	// TODO: improve the performance by using io.Pipe
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to read request body"})
		return
	}

	uuid := hash(body)

	metadata, err := getPhotonFromMetadata(body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to get metadata from zip"})
		return
	}

	metadata.ID = uuid
	now := time.Now()
	metadata.CreatedAt = now.UnixMilli()

	err = CreatePhotonCR(metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to create photon in database"})
		return
	}

	// TODO: failure recovery: if the server crashes here, we should be able to delete the object uploaded to S3

	// Upload to S3
	// TODO: append the content hash to the s3 key as suffix
	s3URL := getPhotonS3ObjectName(metadata.Name, uuid)
	err = uploadToS3(bucketName, s3URL, bytes.NewReader(body))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "Failed", "error": err.Error(), "message": "failed to upload to S3"})
		return
	}

	photonMapRWLock.Lock()
	photonById[uuid] = metadata
	if photonByName[metadata.Name] == nil {
		photonByName[metadata.Name] = make(map[string]*Photon)
	}
	photonByName[metadata.Name][uuid] = metadata
	photonMapRWLock.Unlock()

	c.JSON(http.StatusOK, gin.H{"status": "OK", "message": "created photon: " + uniqName(metadata.Name, uuid)})
}
