package main

import (
	"context"
	"log"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/leptonai/lepton/go-pkg/namedb"
)

var deploymentDB = namedb.NewNameDB[leptonaiv1alpha1.LeptonDeployment]()

func initDeployments() {
	// Initialize the photon database
	lds, err := readAllLeptonDeploymentCR()
	if err != nil {
		log.Fatalln(err)
	}
	deploymentDB.Add(lds...)

	go periodCheckDeploymentState()
}

func periodCheckDeploymentState() {
	tick := time.Tick(5 * time.Second)
	for range tick {
		lds, err := readAllLeptonDeploymentCR()
		if err != nil {
			log.Println("Reading all LeptonDeployment CRs failed:", err.Error())
			continue
		}
		deploymentDB.Add(lds...)
	}
}

func readAllLeptonDeploymentCR() ([]*leptonaiv1alpha1.LeptonDeployment, error) {
	lds := &leptonaiv1alpha1.LeptonDeploymentList{}
	if err := util.K8sClient.List(context.Background(), lds, client.InNamespace(*namespaceFlag)); err != nil {
		return nil, err
	}

	ret := make([]*leptonaiv1alpha1.LeptonDeployment, 0, len(lds.Items))
	for i := range lds.Items {
		ret = append(ret, &lds.Items[i])
	}

	return ret, nil
}
