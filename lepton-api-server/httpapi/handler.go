package httpapi

import (
	"context"
	"time"

	"github.com/leptonai/lepton/go-pkg/datastore"
	"github.com/leptonai/lepton/go-pkg/k8s"
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
	namespace                     string
	prometheusURL                 string
	bucketName                    string
	efsID                         string
	photonPrefix                  string
	s3ReadOnlyAccessK8sSecretName string
	rootDomain                    string
	workspaceName                 string
	certARN                       string
	apiToken                      string
	photonBucket                  *blob.Bucket
	backupBucket                  *blob.Bucket

	secretDB *secret.SecretSet
	phDB     *datastore.CRStore[*leptonaiv1alpha1.Photon]
	ldDB     *datastore.CRStore[*leptonaiv1alpha1.LeptonDeployment]
}

func New(namespace, prometheusURL, bucketName, efsID, protonPrefix, s3ReadOnlyAccessK8sSecretName,
	rootDomain, workspaceName, certARN, apiToken string, photonBucket, backupBucket *blob.Bucket,
	workspaceState WorkspaceState) *Handler {
	k8s.Client.Scheme()
	h := &Handler{
		namespace:                     namespace,
		prometheusURL:                 prometheusURL,
		bucketName:                    bucketName,
		efsID:                         efsID,
		photonPrefix:                  protonPrefix,
		s3ReadOnlyAccessK8sSecretName: s3ReadOnlyAccessK8sSecretName,
		rootDomain:                    rootDomain,
		workspaceName:                 workspaceName,
		certARN:                       certARN,
		apiToken:                      apiToken,
		photonBucket:                  photonBucket,
		backupBucket:                  backupBucket,

		secretDB: secret.New(namespace, secret.SecretObjectName),
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
	h.migratePhotonFilenamePrefixInS3()

	switch workspaceState {
	case WorkspaceStateReady:
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

// TODO: this function is to fix the compatibility issue introduced
// by https://github.com/leptonai/lepton/pull/1568
// Will delete the function while we fully migrated all workspaces
func (h *Handler) migratePhotonFilenamePrefixInS3() {
	phs, err := h.phDB.List(context.Background())
	if err != nil {
		goutil.Logger.Fatalw("failed to list photons",
			"operation", "migratePhotonFilenamePrefixInS3",
			"error", err,
		)
	}
	for _, ph := range phs {
		oldName := ph.GetSpecName() + "-" + ph.GetSpecID()
		newName := ph.GetSpecID()
		exist, err := h.photonBucket.Exists(context.Background(), oldName)
		if err != nil {
			goutil.Logger.Fatalw("failed to check photon file",
				"operation", "migratePhotonFilenamePrefixInS3",
				"error", err,
				"oldName", oldName,
			)
		}
		if exist {
			goutil.Logger.Infow("migrating photon file",
				"operation", "migratePhotonFilenamePrefixInS3",
				"oldName", oldName,
				"newName", newName,
			)
			if err := h.photonBucket.Copy(context.Background(), newName, oldName, nil); err != nil {
				goutil.Logger.Fatalw("failed to copy photon file",
					"operation", "migratePhotonFilenamePrefixInS3",
					"error", err,
					"oldName", oldName,
					"newName", newName,
				)
			}
			if err := h.photonBucket.Delete(context.Background(), oldName); err != nil {
				goutil.Logger.Fatalw("failed to delete photon file",
					"operation", "migratePhotonFilenamePrefixInS3",
					"error", err,
					"oldName", oldName,
				)
			}
		}
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
