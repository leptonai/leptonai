package main

import (
	"archive/zip"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"

	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/namedb"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	"k8s.io/apimachinery/pkg/watch"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

var photonDB *namedb.NameDB[leptonaiv1alpha1.Photon]

func initPhotons() {
	photonDB = namedb.NewNameDB[leptonaiv1alpha1.Photon]()
	// Watch for changes in the LeptonDeployment CR
	ch, err := k8s.Client.Watch(context.Background(),
		&leptonaiv1alpha1.PhotonList{},
		client.InNamespace(*namespaceFlag))
	if err != nil {
		// TODO: better error handling
		log.Fatalln(err)
	}
	// We have to finish processing all events in the channel before
	// continuing the startup process
	log.Println("rebuilding api server state for photons...")
	drainAndProcessExistingEvents(ch.ResultChan(), processPhotonEvent)
	log.Println("restored api server state for photons")
	// Watch for future changes
	go func() {
		log.Println("Photon watcher started")
		defer func() {
			log.Println("Photon watcher exited, restarting...")
			// TODO when we re-initialize the db, users may temporarily see an
			// in-complete list (though the time is very short)
			go initPhotons()
		}()
		for event := range ch.ResultChan() {
			processPhotonEvent(event)
		}
	}()
}

func processPhotonEvent(event watch.Event) {
	ph := event.Object.(*leptonaiv1alpha1.Photon)
	log.Println("Photon CR event:", event.Type, ph.Name)
	switch event.Type {
	case watch.Added:
		photonDB.Add(ph)
	case watch.Modified:
		photonDB.Add(ph)
	case watch.Deleted:
		err := photonBucket.Delete(context.Background(), ph.GetSpecUniqName())
		if err != nil {
			// TODO: we should handle the error to avoid resource leak
			log.Println("failed to delete photon " + ph.GetSpecUniqName() + " from S3: " + err.Error())
		}
		photonDB.Delete(ph)
	}

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
	ph.Name = ph.GetSpecUniqName()
	ph.Namespace = *namespaceFlag

	return ph, nil
}
