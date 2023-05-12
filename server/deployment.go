package main

import (
	"sync"
	"time"
)

type LeptonDeployment struct {
	ID                  string                              `json:"id"`
	CreatedAt           int64                               `json:"created_at"`
	Name                string                              `json:"name"`
	PhotonID            string                              `json:"photon_id"`
	ModelID             string                              `json:"model_id"`
	Status              LeptonDeploymentStatus              `json:"status"`
	ResourceRequirement LeptonDeploymentResourceRequirement `json:"resource_requirement"`
}

type LeptonDeploymentStatus struct {
	State    DeploymentState          `json:"state"`
	Endpoint LeptonDeploymentEndpoint `json:"endpoint"`
}

type LeptonDeploymentEndpoint struct {
	InternalEndpoint string `json:"internal_endpoint"`
	ExternalEndpoint string `json:"external_endpoint"`
}

type LeptonDeploymentResourceRequirement struct {
	CPU             float32 `json:"cpu"`
	Memory          int64   `json:"memory"`
	AcceleratorType string  `json:"accelerator_type"`
	AcceleratorNum  float64 `json:"accelerator_num"`
	MinReplicas     int     `json:"min_replicas"`
}

var (
	deploymentById      = make(map[string]*LeptonDeployment)
	deploymentByName    = make(map[string]*LeptonDeployment)
	deploymentMapRWLock = sync.RWMutex{}
)

func initDeployments() {
	// Initialize the photon database
	metadataList, err := ReadAllLeptonDeploymentCR()
	if err != nil {
		// TODO: better error handling
		panic(err)
	}
	deploymentMapRWLock.Lock()
	defer deploymentMapRWLock.Unlock()
	for _, m := range metadataList {
		deploymentById[m.ID] = m
		deploymentByName[m.Name] = m
	}

	go periodCheckDeploymentState()
}

func periodCheckDeploymentState() {
	for {
		names := make([]string, 0, len(deploymentByName))
		deployments := make([]*LeptonDeployment, 0, len(deploymentByName))
		deploymentMapRWLock.RLock()
		for name, deployment := range deploymentByName {
			names = append(names, name)
			deployments = append(deployments, deployment)
		}
		deploymentMapRWLock.RUnlock()

		states := deploymentState(names...)

		for i := range names {
			if (deployments[i].Status.State == DeploymentStateEmpty) || (deployments[i].Status.State != DeploymentStateUnknown && states[i] != deployments[i].Status.State) {
				deployments[i].Status.State = states[i]
				PatchLeptonDeploymentCR(deployments[i])
			}
		}

		time.Sleep(10 * time.Second)
	}
}
