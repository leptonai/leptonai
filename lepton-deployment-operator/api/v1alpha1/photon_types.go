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
	runtime "k8s.io/apimachinery/pkg/runtime"
)

// PhotonSpec defines the desired state of Photon
type PhotonSpec struct {
	PhotonUserSpec   `json:",inline"`
	PhotonSystemSpec `json:",inline"`
}

// PhotonUserSpec defines the user-controlled spec.
type PhotonUserSpec struct {
	Name string `json:"name"`
	// +optional
	Model string `json:"model"`
	// +optional
	RequirementDependency []string `json:"requirement_dependency"`
	Image                 string   `json:"image"`
	// +optional
	Entrypoint string `json:"entrypoint"`
	// +optional
	ExposedPorts []int32 `json:"exposed_ports"`
	// +optional
	ContainerArgs []string `json:"container_args"`
	// +optional
	OpenAPISchema runtime.RawExtension `json:"openapi_schema"`
}

// PhotonSystemSpec defines the system-controlled spec.
type PhotonSystemSpec struct {
	ID string `json:"id"`
}

// GetSpecName returns the name of the photon.
func (p Photon) GetSpecName() string {
	return p.Spec.Name
}

// GetSpecUniqName returns the unique name of the photon.
func (p Photon) GetSpecUniqName() string {
	return fmt.Sprintf("%s-%s", p.GetSpecName(), p.GetSpecID())
}

// GetSpecID returns the id of the photon.
func (p Photon) GetSpecID() string {
	return p.Spec.ID
}

// SetID sets the id of the photon.
func (p *Photon) SetID(id string) {
	p.Spec.ID = id
}

// GetVersion returns the version of the photon.
func (p Photon) GetVersion() int64 {
	return p.CreationTimestamp.UnixMilli()
}

// PhotonStatus defines the observed state of Photon. It is empty because we only use Photon as a database.
type PhotonStatus struct {
}

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status
//+kubebuilder:resource:shortName=ph

// Photon is the Schema for the photons API
type Photon struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   PhotonSpec   `json:"spec,omitempty"`
	Status PhotonStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// PhotonList contains a list of Photon
type PhotonList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []Photon `json:"items"`
}

func init() {
	SchemeBuilder.Register(&Photon{}, &PhotonList{})
}
