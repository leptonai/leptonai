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
	RootDomain         string   `json:"root_domain,omitempty"`
	CellName           string   `json:"cell_name,omitempty"`
	CertificateARN     string   `json:"certificate_arn,omitempty"`
	APITokens          []string `json:"api_tokens,omitempty"`
}

// LeptonDeploymentStatus defines the user-controlled spec.
type LeptonDeploymentUserSpec struct {
	Name                string                              `json:"name"`
	PhotonID            string                              `json:"photon_id"`
	ResourceRequirement LeptonDeploymentResourceRequirement `json:"resource_requirement"`
	// +optional
	Envs []EnvVar `json:"envs"`
}

// GetSpecName returns the name of the deployment.
func (ld LeptonDeployment) GetSpecName() string {
	return ld.Spec.Name
}

// GetUniqPhotonName returns the unique name of the photon.
func (ld LeptonDeployment) GetUniqPhotonName() string {
	return fmt.Sprintf("%s-%s", ld.Spec.PhotonName, ld.Spec.PhotonID)
}

// GetSpecID returns the ID of the deployment. It equals to the Name.
func (ld LeptonDeployment) GetSpecID() string {
	return ld.GetSpecName()
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
	LeptonDeploymentReplicaResourceRequirement `json:",inline"`
	// +optional
	ResourceShape LeptonDeploymentResourceShape `json:"resource_shape"`
	MinReplicas   int32                         `json:"min_replicas"`
}

type LeptonDeploymentReplicaResourceRequirement struct {
	CPU    float64 `json:"cpu"`
	Memory int64   `json:"memory"`
	// +optional
	AcceleratorType string `json:"accelerator_type"`
	// +optional
	AcceleratorNum float64 `json:"accelerator_num"`
}

type ResourceShape struct {
	// Name of the shape. E.g. "Large"
	Name string `json:"name"`
	// Description of the shape. E.g. "Large shape with 4 CPUs and 16GB of RAM"
	Description string                                     `json:"description"`
	Resource    LeptonDeploymentReplicaResourceRequirement `json:"resource"`
}

// EnvVar defines the environment variable of the deployment.
type EnvVar struct {
	Name      string   `json:"name"`
	Value     string   `json:"value,omitempty"`
	ValueFrom EnvValue `json:"value_from,omitempty"`
}

type EnvValue struct {
	SecretNameRef string `json:"secret_ref,omitempty"`
}

// LeptonDeploymentStatus defines the observed state of LeptonDeployment
type LeptonDeploymentStatus struct {
	State           LeptonDeploymentState    `json:"state"`
	Endpoint        LeptonDeploymentEndpoint `json:"endpoint"`
	ReadinessIssues []string                 `json:"readiness_issues,omitempty"`
}

type LeptonDeploymentResourceShape string

// LeptonDeploymentState defines the state of the deployment.
type LeptonDeploymentState string

const (
	LeptonDeploymentStateRunning  LeptonDeploymentState = "Running"
	LeptonDeploymentStateNotReady LeptonDeploymentState = "Not Ready"
	LeptonDeploymentStateStarting LeptonDeploymentState = "Starting"
	LeptonDeploymentStateUpdating LeptonDeploymentState = "Updating"
	LeptonDeploymentStateUnknown  LeptonDeploymentState = "Unknown"
)

type LeptonDeploymentNotReadyIssue string

const (
	LeptonDeploymentNotReadyIssueNoCapacity         LeptonDeploymentNotReadyIssue = "No Capacity"
	LeptonDeploymentNotReadyIssueConfigurationError LeptonDeploymentNotReadyIssue = "Configuration Error"
	LeptonDeploymentNotReadyIssueCodeError          LeptonDeploymentNotReadyIssue = "Code Error"
	LeptonDeploymentNotReadyIssueUnknown            LeptonDeploymentNotReadyIssue = "Unknown"
)

// LeptonDeploymentEndpoint defines the endpoint of the deployment.
type LeptonDeploymentEndpoint struct {
	InternalEndpoint string `json:"internal_endpoint"`
	ExternalEndpoint string `json:"external_endpoint"`
}

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status
//+kubebuilder:resource:shortName=ld

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
