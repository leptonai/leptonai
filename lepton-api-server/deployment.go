package main

import (
	"fmt"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"

	"github.com/leptonai/lepton/go-pkg/namedb"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	"k8s.io/apimachinery/pkg/api/resource"
)

var deploymentDB = namedb.NewNameDB[httpapi.LeptonDeployment]()

func initDeployments() {
	// Initialize the photon database
	lds, err := ReadAllLeptonDeploymentCR()
	if err != nil {
		// TODO: better error handling
		panic(err)
	}

	deploymentDB.Add(lds...)
	if err := updateLeptonIngress(deploymentDB.GetAll()); err != nil {
		panic(err)
	}

	go periodCheckDeploymentState()
}

func periodCheckDeploymentState() {
	for {
		lds := deploymentDB.GetAll()
		states := deploymentState(lds...)

		for i, ld := range lds {
			if ld.Status.Endpoint.ExternalEndpoint == "" {
				externalEndpoint, err := watchForDeploymentIngressEndpoint(ingressName(ld))
				if err != nil {
					continue
				}
				ld.Status.Endpoint.ExternalEndpoint = externalEndpoint
			}
			if ld.Status.Endpoint.InternalEndpoint == "" {
				ld.Status.Endpoint.InternalEndpoint = fmt.Sprintf("%s.%s.svc.cluster.local:8080", ld.Name, deploymentNamespace)
			}
			if states[i] != httpapi.DeploymentStateUnknown && states[i] != ld.Status.State {
				ld.Status.State = states[i]
			}
		}

		time.Sleep(10 * time.Second)
	}
}

func convertDeploymentToCr(d *httpapi.LeptonDeployment) *leptonaiv1alpha1.LeptonDeploymentSpec {
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

func convertCrToDeployment(cr *leptonaiv1alpha1.LeptonDeploymentSpec) *httpapi.LeptonDeployment {
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
	return &httpapi.LeptonDeployment{
		ID:        cr.ID,
		CreatedAt: cr.CreatedAt,
		Name:      cr.Name,
		PhotonID:  cr.PhotonID,
		ModelID:   cr.ModelID,
		Status: httpapi.LeptonDeploymentStatus{
			State: httpapi.DeploymentStateUnknown,
			Endpoint: httpapi.LeptonDeploymentEndpoint{
				InternalEndpoint: "",
				ExternalEndpoint: "",
			},
		},
		ResourceRequirement: httpapi.LeptonDeploymentResourceRequirement{
			CPU:             cpu.AsApproximateFloat64(),
			Memory:          memory.Value() / 1024 / 1024,
			AcceleratorType: cr.ResourceRequirement.AcceleratorType,
			AcceleratorNum:  acceleratorNum.AsApproximateFloat64(),
			MinReplicas:     cr.ResourceRequirement.MinReplicas,
		},
	}
}
