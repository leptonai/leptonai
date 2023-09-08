package httpapi

import (
	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
)

type LeptonJob struct {
	Metadata Metadata        `json:"metadata"`
	Spec     LeptonJobSpec   `json:"spec"`
	Status   LeptonJobStatus `json:"status,omitempty"`
}

// ref: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.26/#jobspec-v1-batch
type LeptonJobSpec struct {
	// ResourceShape describes the compute resource requirements.
	ResourceShape leptonaiv1alpha1.ResourceShape `json:"resource_shape"`
	// Container to run in the job.
	Container Container `json:"container"`

	// Completions specifies the desired number of successfully finished replicas the job should be run with.
	Completions *int64 `json:"completions"`

	// Parallelism specifies the maximum desired number of replicas the job should run at any given time.
	Parallelism *int64 `json:"parallelism"`

	// +optional, environment variables to set for the container
	Envs []leptonaiv1alpha1.EnvVar `json:"envs"`

	// +optional, volumes to mount for the container
	Mounts []leptonaiv1alpha1.Mount `json:"mounts"`
}

// ref: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.26/#jobstatus-v1-batch
// ref: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase
type LeptonJobStatus struct {
	// number of replicas with phase NotReady
	NotReady int32 `json:"not_ready"`
	// number of replicas with phase Running
	Running int32 `json:"running"`
	// number of replicas which reached phase Failed
	Failed int32 `json:"failed"`
	// number of replicas which reached phase Succeeded
	Succeeded int32 `json:"succeeded"`
	// completion time of job if finished
	CompletionTime int64 `json:"completion_time,omitempty"`
}

// ref: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.27/#container-v1-core
type Container struct {
	Args    []string `json:"args"`
	Command []string `json:"command"`
	Image   string   `json:"image"`
}
