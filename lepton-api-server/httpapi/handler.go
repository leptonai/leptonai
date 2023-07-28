package httpapi

import (
	"context"
	"time"

	"github.com/leptonai/lepton/go-pkg/datastore"
	"github.com/leptonai/lepton/go-pkg/k8s/secret"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"gocloud.dev/blob"
)

// Backupable is an interface for resources that can be backed up
type Backupable interface {
	Backup(ctx context.Context) error
}

type Handler struct {
	clusterName                   string
	namespace                     string
	prometheusURL                 string
	bucketName                    string
	efsID                         string
	photonPrefix                  string
	photonImageRegistry           string
	s3ReadOnlyAccessK8sSecretName string
	rootDomain                    string
	workspaceName                 string
	certARN                       string
	apiToken                      string
	photonBucket                  *blob.Bucket

	secretDB *secret.SecretSet
	phDB     *datastore.CRStore[*leptonaiv1alpha1.Photon]
	ldDB     *datastore.CRStore[*leptonaiv1alpha1.LeptonDeployment]
}

func New(clusterName, namespace, prometheusURL, bucketName, efsID, protonPrefix, photonImageRegistry, s3ReadOnlyAccessK8sSecretName,
	rootDomain, workspaceName, certARN, apiToken string, photonBucket, backupBucket *blob.Bucket,
	workspaceState WorkspaceState) *Handler {
	h := &Handler{
		clusterName:                   clusterName,
		namespace:                     namespace,
		prometheusURL:                 prometheusURL,
		bucketName:                    bucketName,
		efsID:                         efsID,
		photonPrefix:                  protonPrefix,
		photonImageRegistry:           photonImageRegistry,
		s3ReadOnlyAccessK8sSecretName: s3ReadOnlyAccessK8sSecretName,
		rootDomain:                    rootDomain,
		workspaceName:                 workspaceName,
		certARN:                       certARN,
		apiToken:                      apiToken,
		photonBucket:                  photonBucket,

		secretDB: secret.New(namespace, secret.SecretObjectName, backupBucket),
		phDB: datastore.NewCRStore[*leptonaiv1alpha1.Photon](
			namespace,
			&leptonaiv1alpha1.Photon{},
			backupBucket,
		),
		ldDB: datastore.NewCRStore[*leptonaiv1alpha1.LeptonDeployment](
			namespace,
			&leptonaiv1alpha1.LeptonDeployment{},
			backupBucket,
		),
	}

	switch workspaceState {
	case WorkspaceStateNormal:
	case WorkspaceStatePaused:
	case WorkspaceStateTerminated:
		go h.deleteAllDeployments()
	default:
		goutil.Logger.Fatalw("invalid workspace state",
			"state", workspaceState,
		)
	}
	goutil.Logger.Infow("workspace state",
		"state", workspaceState,
	)

	go runBackupsPeriodically(h.phDB)
	go runBackupsPeriodically(h.ldDB)
	go runBackupsPeriodically(h.secretDB)

	return h
}

const (
	deleteAllDeploymentInterval = 5 * time.Minute
)

func (h *Handler) deleteAllDeployments() {
	for {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
		err := h.ldDB.BackupAndDeleteAll(ctx)
		cancel()
		if err != nil {
			goutil.Logger.Errorw("failed to delete all deployments",
				"operation", "deleteAllDeployments",
				"error", err,
			)
		}
		time.Sleep(deleteAllDeploymentInterval)
	}
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

func (h *Handler) ReplicaHandler() *ReplicaHandler {
	return &ReplicaHandler{
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

func (h *Handler) StorageHandler() *StorageHandler {
	return &StorageHandler{
		Handler: *h,
	}
}

func (h *Handler) StorageSyncerHandler() *StorageSyncerHandler {
	return &StorageSyncerHandler{
		Handler: *h,
	}
}

func (h *Handler) DeploymentReadinessHandler() *DeploymentReadinessHandler {
	return &DeploymentReadinessHandler{
		Handler: *h,
	}
}

func (h *Handler) DeploymentTerminationHandler() *DeploymentTerminationHandler {
	return &DeploymentTerminationHandler{
		Handler: *h,
	}
}

const (
	backupPeriod        = 12 * time.Hour
	backupRetryInterval = 5 * time.Minute
)

func runBackupsPeriodically(c Backupable) {
	for {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
		err := c.Backup(ctx)
		cancel()
		if err != nil {
			goutil.Logger.Errorw("failed to backup",
				"operation", "backup",
				"error", err,
			)
			goutil.Logger.Infow("retrying backup after 5 minutes",
				"operation", "backup",
			)
			time.Sleep(backupRetryInterval)
			continue
		}

		goutil.Logger.Infow("backup successful",
			"operation", "backup",
		)
		goutil.Logger.Infof("next backup after %s hours", backupPeriod)
		time.Sleep(backupPeriod)
	}
}
