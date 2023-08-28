package httpapi

type Metadata struct {
	CreatedAt int64  `json:"created_at,omitempty"`
	Name      string `json:"name"`
}
