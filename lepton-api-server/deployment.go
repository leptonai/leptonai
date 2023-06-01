package main

import (
	"fmt"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/leptonai/lepton/go-pkg/namedb"
)

var deploymentDB = namedb.NewNameDB[leptonaiv1alpha1.LeptonDeployment]()

func initDeployments() {
	// Initialize the photon database
	lds, err := ReadAllLeptonDeploymentCR()
	if err != nil {
		// TODO: better error handling
		panic(err)
	}
	deploymentDB.Add(lds...)

	go periodCheckDeploymentState()
}

func periodCheckDeploymentState() {
	for {
		lds := deploymentDB.GetAll()
		states := deploymentState(lds...)

		for i, ld := range lds {
			if len(ld.Status.Endpoint.ExternalEndpoint) == 0 {
				ld.Status.Endpoint.ExternalEndpoint = util.DomainName(ld, rootDomain)
			}
			if len(ld.Status.Endpoint.InternalEndpoint) == 0 {
				ld.Status.Endpoint.InternalEndpoint = fmt.Sprintf("%s.%s.svc.cluster.local:8080", ld.GetName(), deploymentNamespace)
			}
			if states[i] != leptonaiv1alpha1.LeptonDeploymentStateUnknown && states[i] != ld.Status.State {
				ld.Status.State = states[i]
			}
		}

		time.Sleep(10 * time.Second)
	}
}
