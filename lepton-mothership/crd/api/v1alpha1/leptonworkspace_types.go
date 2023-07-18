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

// LeptonWorkspaceSpec defines the desired state of LeptonWorkspace.
// The deployment environment inherits the one from cluster spec.
type LeptonWorkspaceSpec struct {
	// Name is a globally unique name of a workspace within mothership.
	Name        string `json:"name"`
	ClusterName string `json:"cluster_name"`
	ImageTag    string `json:"image_tag,omitempty"`
	APIToken    string `json:"api_token,omitempty"`
	EnableWeb   bool   `json:"enable_web,omitempty"`
	// Terraform module git ref
	GitRef string `json:"git_ref"`
	// +optional
	QuotaGroup string `json:"quota_group"`

	Description string `json:"description"`
}

// LeptonWorkspaceStatus defines the observed state of LeptonWorkspace
type LeptonWorkspaceStatus struct {
	// Previously known workspace state.
	LastState LeptonWorkspaceState `json:"last_state,omitempty"`
	// Current workspace state.
	State LeptonWorkspaceState `json:"state"`
	// unix timestamp
	UpdatedAt uint64 `json:"updated_at"`
}

const (
	WorkspaceStateCreating LeptonWorkspaceState = "creating"
	WorkspaceStateUpdating LeptonWorkspaceState = "updating"
	WorkspaceStateReady    LeptonWorkspaceState = "ready"
	WorkspaceStateFailed   LeptonWorkspaceState = "failed"
	WorkspaceStateDeleting LeptonWorkspaceState = "deleting"
	WorkspaceStateDeleted  LeptonWorkspaceState = "deleted"
	WorkspaceStateUnknown  LeptonWorkspaceState = ""
)

type (
	LeptonWorkspaceState string
)

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status
//+kubebuilder:resource:shortName=lw

// LeptonWorkspace is the Schema for the leptonworkspaces API
type LeptonWorkspace struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   LeptonWorkspaceSpec   `json:"spec,omitempty"`
	Status LeptonWorkspaceStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// LeptonWorkspaceList contains a list of LeptonWorkspace
type LeptonWorkspaceList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []LeptonWorkspace `json:"items"`
}

func init() {
	SchemeBuilder.Register(&LeptonWorkspace{}, &LeptonWorkspaceList{})
}
