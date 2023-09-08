package leptonlabels

const (
	// TODO: Depreciate the old labels
	LabelKeyPhotonNameDepreciated            = "photon_name"
	LabelKeyPhotonIDDepreciated              = "photon_id"
	LabelKeyLeptonDeploymentNameDepreciated  = "lepton_deployment_name"
	LabelKeyLeptonDeploymentShapeDepreciated = "lepton_deployment_shape"

	LabelKeyPhotonName            = "photon.lepton.ai/name"
	LabelKeyPhotonID              = "photon.lepton.ai/id"
	LabelKeyLeptonDeploymentName  = "deployment.lepton.ai/name"
	LabelKeyLeptonDeploymentShape = "deployment.lepton.ai/shape"

	LabelKeyLeptonResourceProvider = "lepton.ai/resource-provider"
)

const (
	LabelValueResourceProviderLambdaLabs = "lambdalabs"
)
