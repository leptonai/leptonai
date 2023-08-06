// Package version defines the "lepton-api-server" version.
package version

var (
	// BuildTime represents the binary built timestamp.
	BuildTime string
	// GitCommit represents the version.
	GitCommit string
)

// TODO: also include semantic version
type Info struct {
	BuildTime string `json:"build_time"`
	GitCommit string `json:"git_commit"`
}

var VersionInfo Info

func init() {
	VersionInfo.BuildTime = BuildTime
	VersionInfo.GitCommit = GitCommit
}

// Release is the version of the lepton-api-server
// TODO: read from branch name or tag
var Release = "0.7.0"
