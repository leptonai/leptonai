package httpapi

import "github.com/leptonai/lepton/go-pkg/namedb"

var (
	prometheusURL = ""
	deploymentDB  *namedb.NameDB[LeptonDeployment]
	photonDB      *namedb.NameDB[Photon]
)

// TODO: create a struct to hold all the handlers and common data
func Init(pURL string, dDB *namedb.NameDB[LeptonDeployment], pDB *namedb.NameDB[Photon]) {
	prometheusURL = pURL
	deploymentDB = dDB
	photonDB = pDB
}
