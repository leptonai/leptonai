package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io"

	"github.com/leptonai/lepton/go-pkg/namedb"
	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"
)

type PhotonCr struct {
	httpapi.PhotonCommon
	OpenApiSchema string `json:"openapi_schema"`
}

var photonDB = namedb.NewNameDB[httpapi.Photon]()

func initPhotons() {
	// Initialize the photon database
	metadataList, err := ReadAllPhotonCR()
	if err != nil {
		// TODO: better error handling
		panic(err)
	}

	photonDB.Add(metadataList...)
}

func convertPhotonToCr(photon *httpapi.Photon) *PhotonCr {
	openApiSchemaBytes, err := json.Marshal(photon.OpenApiSchema)
	if err != nil {
		openApiSchemaBytes = nil
	}
	return &PhotonCr{
		PhotonCommon:  photon.PhotonCommon,
		OpenApiSchema: string(openApiSchemaBytes),
	}
}

func convertCrToPhoton(cr *PhotonCr) *httpapi.Photon {
	var openApiSchema map[string]interface{}
	if err := json.Unmarshal([]byte(cr.OpenApiSchema), &openApiSchema); err != nil {
		openApiSchema = nil
	}
	return &httpapi.Photon{
		PhotonCommon:  cr.PhotonCommon,
		OpenApiSchema: openApiSchema,
	}
}

func getPhotonFromMetadata(body []byte) (*httpapi.Photon, error) {
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
	var metadata httpapi.PhotonMetadata
	if err := json.Unmarshal(metadataBytes, &metadata); err != nil {
		return nil, err
	}
	if !util.ValidateName(metadata.Name) {
		return nil, fmt.Errorf("invalid name %s: %s", metadata.Name, util.NameInvalidMessage)
	}

	var ph httpapi.Photon
	ph.Name = metadata.Name
	ph.Model = metadata.Model
	ph.Image = metadata.Image
	ph.ContainerArgs = metadata.Args
	ph.OpenApiSchema = metadata.OpenApiSchema

	return &ph, nil
}
