package main

import (
	"fmt"
	"sync"
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	"k8s.io/apimachinery/pkg/api/resource"
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
	CPU             float64 `json:"cpu"`
	Memory          int64   `json:"memory"`
	AcceleratorType string  `json:"accelerator_type"`
	AcceleratorNum  float64 `json:"accelerator_num"`
	MinReplicas     int64   `json:"min_replicas"`
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
		lds := make([]*LeptonDeployment, 0, len(deploymentByName))
		deploymentMapRWLock.RLock()
		for name, deployment := range deploymentByName {
			names = append(names, name)
			lds = append(lds, deployment)
		}
		deploymentMapRWLock.RUnlock()

		states := deploymentState(names...)

		for i, ld := range lds {
			if ld.Status.Endpoint.ExternalEndpoint == "" {
				externalEndpoint, err := watchForIngressEndpoint(ingressName(ld))
				if err != nil {
					continue
				}
				ld.Status.Endpoint.ExternalEndpoint = externalEndpoint
			}
			if ld.Status.Endpoint.InternalEndpoint == "" {
				ld.Status.Endpoint.InternalEndpoint = fmt.Sprintf("%s.%s.svc.cluster.local:8080", ld.Name, deploymentNamespace)
			}
			if states[i] != DeploymentStateUnknown && states[i] != ld.Status.State {
				ld.Status.State = states[i]
			}
		}

		time.Sleep(10 * time.Second)
	}
}

func convertDeploymentToCr(d *LeptonDeployment) *leptonaiv1alpha1.LeptonDeploymentSpec {
	return &leptonaiv1alpha1.LeptonDeploymentSpec{
		ID:        d.ID,
		CreatedAt: d.CreatedAt,
		Name:      d.Name,
		PhotonID:  d.PhotonID,
		ModelID:   d.ModelID,
		ResourceRequirement: leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
			CPU:             resource.NewMilliQuantity(int64(d.ResourceRequirement.CPU*1000), resource.DecimalSI).String(),
			Memory:          resource.NewQuantity(d.ResourceRequirement.Memory*1024*1024, resource.BinarySI).String(),
			AcceleratorType: d.ResourceRequirement.AcceleratorType,
			AcceleratorNum:  resource.NewQuantity(int64(d.ResourceRequirement.AcceleratorNum), resource.DecimalSI).String(),
			MinReplicas:     d.ResourceRequirement.MinReplicas,
		},
	}
}

func convertCrToDeployment(cr *leptonaiv1alpha1.LeptonDeploymentSpec) *LeptonDeployment {
	cpu, err := resource.ParseQuantity(cr.ResourceRequirement.CPU)
	if err != nil {
		cpu = resource.MustParse("1")
	}
	memory, err := resource.ParseQuantity(cr.ResourceRequirement.Memory)
	if err != nil {
		// TODO: what value should be set here?
		memory = resource.MustParse("1Gi")
	}
	acceleratorNum, err := resource.ParseQuantity(cr.ResourceRequirement.AcceleratorNum)
	if err != nil {
		acceleratorNum = resource.MustParse("0")
	}
	return &LeptonDeployment{
		ID:        cr.ID,
		CreatedAt: cr.CreatedAt,
		Name:      cr.Name,
		PhotonID:  cr.PhotonID,
		ModelID:   cr.ModelID,
		Status: LeptonDeploymentStatus{
			State: DeploymentStateUnknown,
			Endpoint: LeptonDeploymentEndpoint{
				InternalEndpoint: "",
				ExternalEndpoint: "",
			},
		},
		ResourceRequirement: LeptonDeploymentResourceRequirement{
			CPU:             cpu.AsApproximateFloat64(),
			Memory:          memory.Value() / 1024 / 1024,
			AcceleratorType: cr.ResourceRequirement.AcceleratorType,
			AcceleratorNum:  acceleratorNum.AsApproximateFloat64(),
			MinReplicas:     cr.ResourceRequirement.MinReplicas,
		},
	}
}
