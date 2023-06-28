package httpapi

// StorageSyncer syncs the data from external storage to internal storage.
type StorageSyncer struct {
	Metadata Metadata          `json:"metadata"`
	Spec     StorageSyncerSpec `json:"spec"`
	// TODO: add status
}

// GCSSyncer syncs the data from GCS to EFS.
type GCSSyncer struct {
	GCSURL string `json:"gcs_url"`

	// DestPath is the path under the default EFS root.
	DestPath string `json:"dest_path"`

	// CredJSON is the JSON credential for google cloud.
	CredJSON string `json:"cred_json"`
}

type Metadata struct {
	Name string `json:"name"`
}

type StorageSyncerSpec struct {
	*GCSSyncer
	// TODO: support S3Syncer
}
