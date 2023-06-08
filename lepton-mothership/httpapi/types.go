package httpapi

const (
	ClusterStateCreating = "creating"
	ClusterStateReady    = "ready"
	clusterStateFailed   = "failed"
	ClusterStateDeleting = "deleting"

	ClusterProviderEKS = "aws-eks"

	CellStateCreating = "creating"
	CellStateReady    = "ready"
	CellStateFailed   = "failed"
	CellStateDeleting = "deleting"
)

type (
	ClusterState string
	CellState    string
)

type Cluster struct {
	Spec   ClusterSpec   `json:"spec"`
	Status ClusterStatus `json:"status"`
}

type ClusterSpec struct {
	// Name is a globally unique name of a cluster within mothership.
	Name     string `json:"name"`
	Provider string `json:"provider"`
	Region   string `json:"region"`
	// Terraform module version
	Version string `json:"version"`

	Description string `json:"description"`
}

type ClusterStatus struct {
	State ClusterState `json:"state"`
	// unix timestamp
	UpdatedAt uint64 `json:"updatedAt"`

	Cells []string `json:"cells"`
}

type Cell struct {
	Spec   CellSpec   `json:"spec"`
	Status CellStatus `json:"status"`
}

type CellSpec struct {
	// Name is a globally unique name of a cell within mothership.
	Name   string   `json:"name"`
	Owners []string `json:"owners"`
	// UserTokens maps a user to a list of tokens
	UserTokens map[string][]string `json:"userTokens"`
	// Lepton release version
	Version string `json:"version"`
	Cluster string `json:"cluster"`

	Description string `json:"description"`
}

type CellStatus struct {
	Address string `json:"address"`
	// unix timestamp
	UpdatedAt uint64    `json:"updatedAt"`
	State     CellState `json:"state"`
}
