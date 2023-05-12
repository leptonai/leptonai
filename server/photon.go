package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"io"
	"sync"
)

type PhotonMetadata struct {
	Name          string                 `json:"name"`
	Model         string                 `json:"model"`
	Task          string                 `json:"task"`
	Image         string                 `json:"image"`
	Args          []string               `json:"args"`
	OpenApiSchema map[string]interface{} `json:"openapi_schema"`
}

type PhotonCommon struct {
	ID                    string   `json:"id"`
	Name                  string   `json:"name"`
	Model                 string   `json:"model"`
	RequirementDependency []string `json:"requirement_dependency"`
	Image                 string   `json:"image"`
	Entrypoint            string   `json:"entrypoint"`
	ExposedPorts          []int32  `json:"exposed_ports"`
	ContainerArgs         []string `json:"container_args"`
	CreatedAt             int64    `json:"created_at"`
}

type Photon struct {
	PhotonCommon
	OpenApiSchema string `json:"openapi_schema"`
}

type PhotonOutput struct {
	PhotonCommon
	OpenApiSchema map[string]interface{} `json:"openapi_schema"`
}

var (
	photonById      = make(map[string]*Photon)
	photonByName    = make(map[string]map[string]*Photon)
	photonMapRWLock = sync.RWMutex{}
)

func initPhotons() {
	// Initialize the photon database
	metadataList, err := ReadAllPhotonCR()
	if err != nil {
		// TODO: better error handling
		panic(err)
	}
	photonMapRWLock.Lock()
	defer photonMapRWLock.Unlock()
	for _, m := range metadataList {
		photonById[m.ID] = m
		if photonByName[m.Name] == nil {
			photonByName[m.Name] = make(map[string]*Photon)
		}
		photonByName[m.Name][m.ID] = m
	}
}

func convertPhotonToOutput(photon *Photon) *PhotonOutput {
	openApiSchema := make(map[string]interface{})
	err := json.Unmarshal([]byte(photon.OpenApiSchema), &openApiSchema)
	if err != nil {
		openApiSchema = nil
	}
	return &PhotonOutput{
		PhotonCommon:  photon.PhotonCommon,
		OpenApiSchema: openApiSchema,
	}
}

func getPhotonFromMetadata(body []byte) (*Photon, error) {
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
		return nil, err
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
	var photon Photon
	var metadata PhotonMetadata
	if err := json.Unmarshal(metadataBytes, &metadata); err != nil {
		return nil, err
	}

	photon.Name = metadata.Name
	photon.Model = metadata.Model
	photon.Image = metadata.Image
	photon.ContainerArgs = metadata.Args
	openApiSchema, err := json.Marshal(metadata.OpenApiSchema)
	if err != nil {
		return nil, err
	}
	photon.OpenApiSchema = string(openApiSchema)

	return &photon, nil
}
