package httpapi

type LeptonDeployment struct {
	ID                  string                              `json:"id"`
	CreatedAt           int64                               `json:"created_at"`
	Name                string                              `json:"name"`
	PhotonID            string                              `json:"photon_id"`
	ModelID             string                              `json:"model_id"`
	Status              LeptonDeploymentStatus              `json:"status"`
	ResourceRequirement LeptonDeploymentResourceRequirement `json:"resource_requirement"`
}

func (ld *LeptonDeployment) Merge(p *LeptonDeployment) {
	if p.PhotonID != "" {
		ld.PhotonID = p.PhotonID
	}
	if p.ResourceRequirement.MinReplicas > 0 {
		ld.ResourceRequirement.MinReplicas = p.ResourceRequirement.MinReplicas
	}
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

func (ld LeptonDeployment) GetName() string {
	return ld.Name
}

func (ld LeptonDeployment) GetID() string {
	return ld.ID
}

func (ld LeptonDeployment) GetVersion() int64 {
	return 0
}

type DeploymentState string

const (
	DeploymentStateRunning  DeploymentState = "Running"
	DeploymentStateNotReady DeploymentState = "Not Ready"
	DeploymentStateStarting DeploymentState = "Starting"
	DeploymentStateUpdating DeploymentState = "Updating"
	DeploymentStateUnknown  DeploymentState = "Unknown"
)
