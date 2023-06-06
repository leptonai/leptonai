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

// LeptonDeploymentSpec defines the desired state of LeptonDeployment
type LeptonDeploymentSpec struct {
	LeptonDeploymentSystemSpec `json:",inline"`
	LeptonDeploymentUserSpec   `json:",inline"`
}

// LeptonDeploymentStatus defines the system-controlled spec.
type LeptonDeploymentSystemSpec struct {
	PhotonName         string   `json:"photon_name"`
	PhotonImage        string   `json:"photon_image"`
	BucketName         string   `json:"bucket_name"`
	PhotonPrefix       string   `json:"photon_prefix"`
	ServiceAccountName string   `json:"service_account_name"`
	RootDomain         string   `json:"root_domain"`
	APITokens          []string `json:"api_tokens"`
	CertificateARN     string   `json:"certificate_arn"`
}

// LeptonDeploymentStatus defines the user-controlled spec.
type LeptonDeploymentUserSpec struct {
	Name                string                              `json:"name"`
	PhotonID            string                              `json:"photon_id"`
	ResourceRequirement LeptonDeploymentResourceRequirement `json:"resource_requirement"`
	Envs                []EnvVar                            `json:"envs"`
}

// GetName returns the name of the deployment.
func (ld LeptonDeployment) GetName() string {
	return ld.Spec.Name
}

// GetUniqPhotonName returns the unique name of the photon.
func (ld LeptonDeployment) GetUniqPhotonName() string {
	return fmt.Sprintf("%s-%s", ld.Spec.PhotonName, ld.Spec.PhotonID)
}

// GetID returns the ID of the deployment. It equals to the Name.
func (ld LeptonDeployment) GetID() string {
	return ld.GetName()
}

// GetVersion returns the version of the deployment, which is always 0 because we don't support versioning.
func (ld LeptonDeployment) GetVersion() int64 {
	return 0
}

// Patch modifies the deployment with the given user spec. It only supports PhotonID and MinReplicas for now.
func (ld *LeptonDeployment) Patch(p *LeptonDeploymentUserSpec) {
	if p.PhotonID != "" {
		ld.Spec.PhotonID = p.PhotonID
	}
	if p.ResourceRequirement.MinReplicas > 0 {
		ld.Spec.ResourceRequirement.MinReplicas = p.ResourceRequirement.MinReplicas
	}
}

// LeptonDeploymentResourceRequirement defines the resource requirement of the deployment.
type LeptonDeploymentResourceRequirement struct {
	CPU             float64 `json:"cpu"`
	Memory          int64   `json:"memory"`
	AcceleratorType string  `json:"accelerator_type"`
	AcceleratorNum  float64 `json:"accelerator_num"`
	MinReplicas     int32   `json:"min_replicas"`
}

// EnvVar defines the environment variable of the deployment.
type EnvVar struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

// LeptonDeploymentStatus defines the observed state of LeptonDeployment
type LeptonDeploymentStatus struct {
	State    LeptonDeploymentState    `json:"state"`
	Endpoint LeptonDeploymentEndpoint `json:"endpoint"`
}

// LeptonDeploymentState defines the state of the deployment.
type LeptonDeploymentState string

const (
	LeptonDeploymentStateRunning  LeptonDeploymentState = "Running"
	LeptonDeploymentStateNotReady LeptonDeploymentState = "Not Ready"
	LeptonDeploymentStateStarting LeptonDeploymentState = "Starting"
	LeptonDeploymentStateUpdating LeptonDeploymentState = "Updating"
	LeptonDeploymentStateUnknown  LeptonDeploymentState = "Unknown"
)

// LeptonDeploymentEndpoint defines the endpoint of the deployment.
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
