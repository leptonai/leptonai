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
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// LeptonCellSpec defines the desired state of LeptonCell
type LeptonCellSpec struct {
	// Name is a globally unique name of a cell within mothership.
	Name        string `json:"name"`
	ClusterName string `json:"cluster_name"`
	ImageTag    string `json:"image_tag,omitempty"`
	APIToken    string `json:"api_token,omitempty"`
	EnableWeb   bool   `json:"enable_web,omitempty"`
	// Terraform module version
	Version string `json:"version"`

	Description string `json:"description"`
}

// LeptonCellStatus defines the observed state of LeptonCell
type LeptonCellStatus struct {
	State LeptonCellState `json:"state"`
	// unix timestamp
	UpdatedAt uint64 `json:"updated_at"`
}

const (
	CellStateCreating = "creating"
	CellStateUpdating = "updating"
	CellStateReady    = "ready"
	CellStateFailed   = "failed"
	CellStateDeleting = "deleting"
	CellStateUnknown  = ""
)

type (
	LeptonCellState string
)

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status
//+kubebuilder:resource:shortName=ce

// LeptonCell is the Schema for the leptoncells API
type LeptonCell struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   LeptonCellSpec   `json:"spec,omitempty"`
	Status LeptonCellStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// LeptonCellList contains a list of LeptonCell
type LeptonCellList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []LeptonCell `json:"items"`
}

func init() {
	SchemeBuilder.Register(&LeptonCell{}, &LeptonCellList{})
}
