package main

import (
	"sync"
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
	State    string                   `json:"state"`
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
	deploymentByName    = make(map[string]map[string]*LeptonDeployment)
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
		if deploymentByName[m.Name] == nil {
			deploymentByName[m.Name] = make(map[string]*LeptonDeployment)
		}
		deploymentByName[m.Name][m.ID] = m
	}
}
