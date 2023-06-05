package main

import (
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/leptonai/lepton/go-pkg/namedb"
)

var deploymentDB = namedb.NewNameDB[leptonaiv1alpha1.LeptonDeployment]()

func initDeployments() {
	// Initialize the photon database
	lds, err := ReadAllLeptonDeploymentCR()
	if err != nil {
		panic(err)
	}
	deploymentDB.Add(lds...)

	go periodCheckDeploymentState()
}

func periodCheckDeploymentState() {
	tick := time.Tick(5 * time.Second)
	for range tick {
		if lds, err := ReadAllLeptonDeploymentCR(); err == nil {
			deploymentDB.Add(lds...)
		}
	}
}
