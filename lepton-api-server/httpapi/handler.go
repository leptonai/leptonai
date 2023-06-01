package httpapi

import (
	"github.com/leptonai/lepton/go-pkg/namedb"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

var (
	prometheusURL = ""
	deploymentDB  *namedb.NameDB[leptonaiv1alpha1.LeptonDeployment]
	photonDB      *namedb.NameDB[leptonaiv1alpha1.Photon]
)

// TODO: create a struct to hold all the handlers and common data
func Init(pURL string, dDB *namedb.NameDB[leptonaiv1alpha1.LeptonDeployment], pDB *namedb.NameDB[leptonaiv1alpha1.Photon]) {
	prometheusURL = pURL
	deploymentDB = dDB
	photonDB = pDB
}
