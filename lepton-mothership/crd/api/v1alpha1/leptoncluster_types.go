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

// LeptonClusterSpec defines the desired state of LeptonCluster
type LeptonClusterSpec struct {
	// Name is a globally unique name of a cluster within mothership.
	Name     string `json:"name"`
	Provider string `json:"provider"`
	Region   string `json:"region"`
	// Terraform module version
	Version string `json:"version"`

	Description string `json:"description"`
}

// LeptonClusterStatus defines the observed state of LeptonCluster
type LeptonClusterStatus struct {
	State LeptonClusterState `json:"state"`
	// unix timestamp
	UpdatedAt uint64 `json:"updated_at"`
	// Workspaces are mutable and can be added/removed from cluster.
	Workspaces []string `json:"workspaces,omitempty"`
	// Properties are immutable and are set once cluster is created.
	Properties LeptonClusterProperties `json:"properties,omitempty"`
}

type LeptonClusterProperties struct {
	OIDCID            string   `json:"oidc_id,omitempty"`
	VPCID             string   `json:"vpc_id,omitempty"`
	VPCPrivateSubnets []string `json:"vpc_private_subnets,omitempty"`
	VPCPublicSubnets  []string `json:"vpc_public_subnets,omitempty"`
}

const (
	ClusterStateCreating = "creating"
	ClusterStateUpdating = "updating"
	ClusterStateReady    = "ready"
	ClusterStateFailed   = "failed"
	ClusterStateDeleting = "deleting"
	ClusterStateUnknown  = ""
)

type (
	LeptonClusterState string
)

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status
//+kubebuilder:resource:shortName=lc

// LeptonCluster is the Schema for the leptonclusters API
type LeptonCluster struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   LeptonClusterSpec   `json:"spec,omitempty"`
	Status LeptonClusterStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// LeptonClusterList contains a list of LeptonCluster
type LeptonClusterList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []LeptonCluster `json:"items"`
}

func init() {
	SchemeBuilder.Register(&LeptonCluster{}, &LeptonClusterList{})
}
