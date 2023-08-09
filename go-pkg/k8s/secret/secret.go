package secret

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"gocloud.dev/blob"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
)

const (
	// ImagePullSecretPrefix is the prefix of the image pull secret.
	ImagePullSecretPrefix = "lepton-image-pull-secret-"
)

type SecretSet struct {
	namespacedName types.NamespacedName
	backupBucket   *blob.Bucket
}

type SecretItem struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

// DockerConfigJSON represents a local docker auth config file
// for pulling images.
// Copied from Kubelet codebase
type DockerConfigJSON struct {
	Auths DockerConfig `json:"auths" datapolicy:"token"`
	// +optional
	HttpHeaders map[string]string `json:"HttpHeaders,omitempty" datapolicy:"token"`
}

// DockerConfig represents the config file used by the docker CLI.
// This config that represents the credentials that should be used
// when pulling images from specific image repositories.
// Copied from Kubelet codebase
type DockerConfig map[string]DockerConfigEntry

// DockerConfigEntry holds the user information that grant the access to docker registry
// Copied from Kubelet codebase
type DockerConfigEntry struct {
	Username string `json:"username,omitempty"`
	Password string `json:"password,omitempty" datapolicy:"password"`
	Email    string `json:"email,omitempty"`
	Auth     string `json:"auth,omitempty" datapolicy:"token"`
}

// New creates a new secret set.
func New(namespace, secretSetName string, backupBucket *blob.Bucket) *SecretSet {
	return &SecretSet{
		namespacedName: types.NamespacedName{
			Namespace: namespace,
			Name:      secretSetName,
		},
		backupBucket: backupBucket,
	}
}

// List lists the keys in the secret set.
func (s *SecretSet) List(ctx context.Context) ([]string, error) {
	secret := &corev1.Secret{}
	err := k8s.MustLoadDefaultClient().Get(ctx, s.namespacedName, secret)
	if apierrors.IsNotFound(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	ret := make([]string, 0, len(secret.Data))
	for key := range secret.Data {
		ret = append(ret, key)
	}
	return ret, nil
}

// Put puts the specified secrets into the secret set.
func (s *SecretSet) Put(ctx context.Context, secrets []SecretItem) error {
	secret := &corev1.Secret{}
	err := k8s.MustLoadDefaultClient().Get(ctx, s.namespacedName, secret)
	exist := true
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		secret = &corev1.Secret{
			ObjectMeta: metav1.ObjectMeta{
				Name:      s.namespacedName.Name,
				Namespace: s.namespacedName.Namespace,
			},
		}
		exist = false
	}
	// have to initialize the map for both update and create, because StringData
	// is write only and get always returns a nil map
	secret.StringData = make(map[string]string)
	for _, item := range secrets {
		if len(item.Value) > 0 {
			secret.StringData[item.Name] = item.Value
		}
	}
	if exist {
		return k8s.MustLoadDefaultClient().Update(ctx, secret)
	}
	return k8s.MustLoadDefaultClient().Create(ctx, secret)
}

// PutPrivateRegistry puts the specified private registry credentials into the secret set.
func (s *SecretSet) PutPrivateRegistry(ctx context.Context, server, username, password, email string) error {
	secret := &corev1.Secret{}
	exist := true

	err := k8s.MustLoadDefaultClient().Get(ctx, s.namespacedName, secret)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		secret = &corev1.Secret{
			ObjectMeta: metav1.ObjectMeta{
				Name:      s.namespacedName.Name,
				Namespace: s.namespacedName.Namespace,
			},
			Type: corev1.SecretTypeDockerConfigJson,
		}
		exist = false
	}
	if secret.Type != corev1.SecretTypeDockerConfigJson {
		return fmt.Errorf("secret %s is not a docker config secret", s.namespacedName.String())
	}

	dockerConfigJSONContent, err := handleDockerCfgJSONContent(username, password, email, server)
	if err != nil {
		return err
	}
	// have to initialize the map for both update and create, because StringData
	// is write only and get always returns a nil map
	secret.Data = make(map[string][]byte)
	secret.Data[corev1.DockerConfigJsonKey] = dockerConfigJSONContent

	if exist {
		return k8s.MustLoadDefaultClient().Update(ctx, secret)
	}
	return k8s.MustLoadDefaultClient().Create(ctx, secret)
}

// Delete deletes the specified keys from the secret set.
func (s *SecretSet) Delete(ctx context.Context, keys ...string) error {
	secret := &corev1.Secret{}
	err := k8s.MustLoadDefaultClient().Get(ctx, s.namespacedName, secret)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		return nil
	}
	for _, key := range keys {
		delete(secret.Data, key)
	}
	return k8s.MustLoadDefaultClient().Update(ctx, secret)
}

// Destroy deletes the secret set.
func (s *SecretSet) Destroy(ctx context.Context) error {
	secret := &corev1.Secret{}
	err := k8s.MustLoadDefaultClient().Get(ctx, s.namespacedName, secret)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		return nil
	}
	return k8s.MustLoadDefaultClient().Delete(ctx, secret)
}

// Backup uploads the secret set to the backup bucket.
func (s *SecretSet) Backup(ctx context.Context) error {
	kind := "Secret"
	secret := &corev1.Secret{}
	err := k8s.MustLoadDefaultClient().Get(ctx, s.namespacedName, secret)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		goutil.Logger.Infow("no Secret found, skipping backup",
			"operation", "backup",
			"kind", kind,
		)
		return nil
	}
	secretData, err := secret.Marshal()
	if err != nil {
		return err
	}

	uploadFilename := fmt.Sprintf("backup-%s-%s.data", kind, time.Now().Format("2006-01-02T15:04:05"))

	err = s.backupBucket.WriteAll(ctx, uploadFilename, secretData, nil)
	if err != nil {
		return err
	}

	goutil.Logger.Infow("uploaded backup",
		"operation", "backup",
		"kind", kind,
		"filename", uploadFilename,
		"size", len(secretData),
	)
	return nil
}

// handleDockerCfgJSONContent serializes a ~/.docker/config.json file
// Copied from Kubelet codebase
func handleDockerCfgJSONContent(username, password, email, server string) ([]byte, error) {
	dockerConfigAuth := DockerConfigEntry{
		Username: username,
		Password: password,
		Email:    email,
		Auth:     encodeDockerConfigFieldAuth(username, password),
	}
	dockerConfigJSON := DockerConfigJSON{
		Auths: map[string]DockerConfigEntry{server: dockerConfigAuth},
	}

	return json.Marshal(dockerConfigJSON)
}

// encodeDockerConfigFieldAuth returns base64 encoding of the username and password string
// Copied from Kubelet codebase
func encodeDockerConfigFieldAuth(username, password string) string {
	fieldValue := username + ":" + password
	return base64.StdEncoding.EncodeToString([]byte(fieldValue))
}
