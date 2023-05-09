package main

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"time"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

// Specify the bucket and key of the object to update
var (
	region       = "us-east-1"
	bucketName   = "leptonai"
	photonPrefix = "photons/"
)

func testS3Permission() {
	currentTime := time.Now()
	testData := []byte(currentTime.Format("2006-01-02 15:04:05"))
	err := uploadToS3(bucketName, "test-permission", bytes.NewReader(testData))
	if err != nil {
		panic(err)
	}
}

func mustInitS3Client() (*s3.Client, error) {
	// Load AWS configuration from the environment or shared config file
	cfg, err := config.LoadDefaultConfig(context.Background())
	if err != nil {
		return nil, fmt.Errorf("error loading AWS config: %v", err)
	}
	cfg.Region = region

	// Create an S3 client using the loaded AWS configuration
	svc := s3.NewFromConfig(cfg)

	return svc, nil
}

func deleteS3Object(bucketName, key string) error {
	svc, err := mustInitS3Client()
	if err != nil {
		return err
	}

	svc.DeleteObject(context.Background(), &s3.DeleteObjectInput{
		Bucket: &bucketName,
		Key:    &key,
	})
	if err != nil {
		return fmt.Errorf("error deleting object: %v", err)
	}

	return nil
}

func uploadToS3(bucketName, key string, content io.Reader) error {
	svc, err := mustInitS3Client()
	if err != nil {
		return err
	}

	// Create a new object with updated content
	_, err = svc.PutObject(context.Background(), &s3.PutObjectInput{
		Bucket: &bucketName,
		Key:    &key,
		Body:   content,
	})
	if err != nil {
		return fmt.Errorf("error updating object: %v", err)
	}

	fmt.Println("Photon uploaded successfully!")
	return nil
}

func downloadFromS3(bucketName, key string) (io.Reader, error) {
	svc, err := mustInitS3Client()
	if err != nil {
		return nil, err
	}

	// Create a new object with updated content
	resp, err := svc.GetObject(context.Background(), &s3.GetObjectInput{
		Bucket: &bucketName,
		Key:    &key,
	})
	if err != nil {
		return nil, err
	}

	return resp.Body, nil
}

func getPhotonS3ObjectName(name, uuid string) string {
	return photonPrefix + uniqName(name, uuid)
}
