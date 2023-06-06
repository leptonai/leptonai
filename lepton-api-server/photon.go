package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io"

	"github.com/leptonai/lepton/go-pkg/namedb"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

var photonDB = namedb.NewNameDB[leptonaiv1alpha1.Photon]()

func initPhotons() {
	// Initialize the photon database
	dynamicClient := util.MustInitK8sDynamicClient()
	phs, err := ReadAllPhotonCR(dynamicClient)
	if err != nil {
		// TODO: better error handling
		panic(err)
	}

	photonDB.Add(phs...)
}

func getPhotonFromMetadata(body []byte) (*leptonaiv1alpha1.Photon, error) {
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
	if err := json.Unmarshal(metadataBytes, &ph.Spec.PhotonUserSpec); err != nil {
		return nil, err
	}
	if !util.ValidateName(ph.Spec.Name) {
		return nil, fmt.Errorf("invalid name %s: %s", ph.Spec.Name, util.NameInvalidMessage)
	}
	ph.SetID(util.HexHash(body))

	return ph, nil
}
