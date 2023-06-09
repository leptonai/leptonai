package httpapi

const (
	CellStateCreating = "creating"
	CellStateReady    = "ready"
	CellStateFailed   = "failed"
	CellStateDeleting = "deleting"
)

type (
	CellState string
)

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
