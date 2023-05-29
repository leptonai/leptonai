package httpapi

type PhotonMetadata struct {
	Name          string                 `json:"name"`
	Model         string                 `json:"model"`
	Task          string                 `json:"task"`
	Image         string                 `json:"image"`
	Args          []string               `json:"args"`
	OpenApiSchema map[string]interface{} `json:"openapi_schema"`
}

type PhotonCommon struct {
	ID                    string   `json:"id"`
	Name                  string   `json:"name"`
	Model                 string   `json:"model"`
	RequirementDependency []string `json:"requirement_dependency"`
	Image                 string   `json:"image"`
	Entrypoint            string   `json:"entrypoint"`
	ExposedPorts          []int32  `json:"exposed_ports"`
	ContainerArgs         []string `json:"container_args"`
	CreatedAt             int64    `json:"created_at"`
}

type Photon struct {
	PhotonCommon
	OpenApiSchema map[string]interface{} `json:"openapi_schema"`
}

func (p Photon) GetName() string {
	return p.Name
}

func (p Photon) GetID() string {
	return p.ID
}

func (p Photon) GetVersion() int64 {
	return p.CreatedAt
}
