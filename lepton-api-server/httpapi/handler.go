package httpapi

import (
	"github.com/leptonai/lepton/go-pkg/namedb"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	"gocloud.dev/blob"
)

type Handler struct {
	namespace          string
	prometheusURL      string
	bucketName         string
	photonPrefix       string
	serviceAccountName string
	rootDomain         string
	certARN            string
	apiToken           string

	photonDB     *namedb.NameDB[leptonaiv1alpha1.Photon]
	deploymentDB *namedb.NameDB[leptonaiv1alpha1.LeptonDeployment]
	photonBucket *blob.Bucket
}

func New(namespace, prometheusURL, bucketName, protonPrefix, serviceAccountName,
	rootDomain, certARN, apiToken string, photonBucket *blob.Bucket) *Handler {
	h := &Handler{
		namespace:          namespace,
		prometheusURL:      prometheusURL,
		bucketName:         bucketName,
		photonPrefix:       protonPrefix,
		serviceAccountName: serviceAccountName,
		rootDomain:         rootDomain,
		certARN:            certARN,
		apiToken:           apiToken,
		photonBucket:       photonBucket,

		photonDB:     namedb.NewNameDB[leptonaiv1alpha1.Photon](),
		deploymentDB: namedb.NewNameDB[leptonaiv1alpha1.LeptonDeployment](),
	}
	h.PhotonHanlder().init()
	h.DeploymentHandler().init()
	return h
}

func (h *Handler) PhotonHanlder() *PhotonHandler {
	return &PhotonHandler{
		Handler: *h,
	}
}

func (h *Handler) DeploymentHandler() *DeploymentHandler {
	return &DeploymentHandler{
		Handler: *h,
	}
}

func (h *Handler) MonitoringHandler() *MonitorningHandler {
	return &MonitorningHandler{
		Handler: *h,
	}
}

func (h *Handler) InstanceHandler() *InstanceHandler {
	return &InstanceHandler{
		Handler: *h,
	}
}
