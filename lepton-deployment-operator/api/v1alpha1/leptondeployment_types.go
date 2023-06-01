/*
Copyright 2023.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package v1alpha1

import (
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// EDIT THIS FILE!  THIS IS SCAFFOLDING FOR YOU TO OWN!
// NOTE: json tags are required.  Any new fields you add must have json tags for the fields to be serialized.

// LeptonDeploymentSpec defines the desired state of LeptonDeployment
type LeptonDeploymentSpec struct {
	// INSERT ADDITIONAL SPEC FIELDS - desired state of cluster
	// Important: Run "make" to regenerate code after modifying this file

	LeptonDeploymentUserSpec `json:",inline"`
	Photon                   *PhotonSpec `json:"photon"`
}

type LeptonDeploymentUserSpec struct {
	Name                string                              `json:"name"`
	PhotonID            string                              `json:"photon_id"`
	ResourceRequirement LeptonDeploymentResourceRequirement `json:"resource_requirement"`
	Envs                []EnvVar                            `json:"envs,omitempty"`
}

func (ld LeptonDeployment) GetName() string {
	return ld.Spec.Name
}

func (ld LeptonDeployment) GetUniqName() string {
	return fmt.Sprintf("%s-%s", ld.GetName(), ld.GetID())
}

func (ld LeptonDeployment) GetID() string {
	if ld.Annotations == nil {
		return ""
	}
	return ld.Annotations["lepton.ai/id"]
}

func (ld *LeptonDeployment) SetID(id string) {
	if ld.Annotations == nil {
		ld.Annotations = make(map[string]string)
	}
	ld.Annotations["lepton.ai/id"] = id
}

func (ld LeptonDeployment) GetVersion() int64 {
	return 0
}

// Patch only supports PhotonID and MinReplicas for now
func (ld *LeptonDeployment) Patch(p *LeptonDeploymentUserSpec) {
	if p.PhotonID != "" {
		ld.Spec.PhotonID = p.PhotonID
	}
	if p.ResourceRequirement.MinReplicas > 0 {
		ld.Spec.ResourceRequirement.MinReplicas = p.ResourceRequirement.MinReplicas
	}
}

type LeptonDeploymentResourceRequirement struct {
	CPU             float64 `json:"cpu"`
	Memory          int64   `json:"memory"`
	AcceleratorType string  `json:"accelerator_type,omitempty"`
	AcceleratorNum  float64 `json:"accelerator_num,omitempty"`
	MinReplicas     int64   `json:"min_replicas"`
}

type EnvVar struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

// LeptonDeploymentStatus defines the observed state of LeptonDeployment
type LeptonDeploymentStatus struct {
	// INSERT ADDITIONAL STATUS FIELD - define observed state of cluster
	// Important: Run "make" to regenerate code after modifying this file

	State    LeptonDeploymentState    `json:"state"`
	Endpoint LeptonDeploymentEndpoint `json:"endpoint"`
}

type LeptonDeploymentState string

const (
	LeptonDeploymentStateRunning  LeptonDeploymentState = "Running"
	LeptonDeploymentStateNotReady LeptonDeploymentState = "Not Ready"
	LeptonDeploymentStateStarting LeptonDeploymentState = "Starting"
	LeptonDeploymentStateUpdating LeptonDeploymentState = "Updating"
	LeptonDeploymentStateUnknown  LeptonDeploymentState = "Unknown"
)

type LeptonDeploymentEndpoint struct {
	InternalEndpoint string `json:"internal_endpoint"`
	ExternalEndpoint string `json:"external_endpoint"`
}

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status

// LeptonDeployment is the Schema for the leptondeployments API
type LeptonDeployment struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   LeptonDeploymentSpec   `json:"spec,omitempty"`
	Status LeptonDeploymentStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// LeptonDeploymentList contains a list of LeptonDeployment
type LeptonDeploymentList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []LeptonDeployment `json:"items"`
}

func init() {
	SchemeBuilder.Register(&LeptonDeployment{}, &LeptonDeploymentList{})
}
