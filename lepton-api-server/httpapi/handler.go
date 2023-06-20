package httpapi

import (
	"github.com/leptonai/lepton/go-pkg/datastore"
	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/k8s/secret"
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
	cellName           string
	certARN            string
	apiToken           string
	photonBucket       *blob.Bucket

	secretDB *secret.SecretSet
	phDB     *datastore.CRStore[*leptonaiv1alpha1.Photon]
	ldDB     *datastore.CRStore[*leptonaiv1alpha1.LeptonDeployment]
}

func New(namespace, prometheusURL, bucketName, protonPrefix, serviceAccountName,
	rootDomain, cellName, certARN, apiToken string, photonBucket *blob.Bucket) *Handler {
	k8s.Client.Scheme()
	h := &Handler{
		namespace:          namespace,
		prometheusURL:      prometheusURL,
		bucketName:         bucketName,
		photonPrefix:       protonPrefix,
		serviceAccountName: serviceAccountName,
		rootDomain:         rootDomain,
		cellName:           cellName,
		certARN:            certARN,
		apiToken:           apiToken,
		photonBucket:       photonBucket,

		secretDB: secret.New(namespace, secret.SecretObjectName),
		phDB:     datastore.NewCRStore[*leptonaiv1alpha1.Photon](namespace, &leptonaiv1alpha1.Photon{}),
		ldDB:     datastore.NewCRStore[*leptonaiv1alpha1.LeptonDeployment](namespace, &leptonaiv1alpha1.LeptonDeployment{}),
	}
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

func (h *Handler) SecretHandler() *SecretHandler {
	return &SecretHandler{
		Handler: *h,
	}
}

func (h *Handler) DeploymentEventHandler() *DeploymentEventHandler {
	return &DeploymentEventHandler{
		Handler: *h,
	}
}
