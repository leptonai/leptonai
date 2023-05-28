package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io"

	"github.com/leptonai/lepton/go-pkg/namedb"
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
	OpenApiSchema map[string]interface{} `json:"openapi_schema"`
}

type PhotonCr struct {
	PhotonCommon
	OpenApiSchema string `json:"openapi_schema"`
}

func (p Photon) GetName() string {
	return p.Name
}

func (p Photon) GetID() string {
	return p.ID
}

func (p Photon) GetVersion() int64 {
	return p.CreatedAt
}

var photonDB = namedb.NewNameDB[Photon]()

func initPhotons() {
	// Initialize the photon database
	metadataList, err := ReadAllPhotonCR()
	if err != nil {
		// TODO: better error handling
		panic(err)
	}

	photonDB.Add(metadataList...)
}

func convertPhotonToCr(photon *Photon) *PhotonCr {
	openApiSchemaBytes, err := json.Marshal(photon.OpenApiSchema)
	if err != nil {
		openApiSchemaBytes = nil
	}
	return &PhotonCr{
		PhotonCommon:  photon.PhotonCommon,
		OpenApiSchema: string(openApiSchemaBytes),
	}
}

func convertCrToPhoton(cr *PhotonCr) *Photon {
	var openApiSchema map[string]interface{}
	if err := json.Unmarshal([]byte(cr.OpenApiSchema), &openApiSchema); err != nil {
		openApiSchema = nil
	}
	return &Photon{
		PhotonCommon:  cr.PhotonCommon,
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
	var metadata PhotonMetadata
	if err := json.Unmarshal(metadataBytes, &metadata); err != nil {
		return nil, err
	}
	if !validateName(metadata.Name) {
		return nil, fmt.Errorf("invalid name %s: %s", metadata.Name, nameValidationMessage)
	}

	var ph Photon
	ph.Name = metadata.Name
	ph.Model = metadata.Model
	ph.Image = metadata.Image
	ph.ContainerArgs = metadata.Args
	ph.OpenApiSchema = metadata.OpenApiSchema

	return &ph, nil
}
