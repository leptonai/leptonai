package goclient

import (
	"encoding/json"
	"net/http"

	"github.com/leptonai/lepton/api-server/httpapi"
)

const (
	imagePullSecretsPath = "/imagepullsecrets"
)

type ImagePullSecret struct {
	Lepton
}

// Create creates a new image pull secret.
func (l *ImagePullSecret) Create(imagePullSecretName, server, user, password, email string) error {
	ips := httpapi.ImagePullSecret{
		Metadata: httpapi.Metadata{
			Name: imagePullSecretName,
		},
		Spec: httpapi.ImagePullSecretSpec{
			RegistryServer: server,
			Username:       user,
			Password:       password,
			Email:          email,
		},
	}

	body, err := json.Marshal(ips)
	if err != nil {
		return err
	}

	header := map[string]string{
		"Content-Type": "application/json",
	}

	_, err = l.http.RequestPath(http.MethodPost, imagePullSecretsPath, header, body)
	if err != nil {
		return err
	}
	return nil
}

// List lists all image pull secrets.
func (l *ImagePullSecret) List() ([]httpapi.ImagePullSecret, error) {
	output, err := l.http.RequestPath(http.MethodGet, imagePullSecretsPath, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := []httpapi.ImagePullSecret{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}

// Delete deletes an image pull secret.
func (l *ImagePullSecret) Delete(imagePullSecretName string) error {
	_, err := l.http.RequestPath(http.MethodDelete, imagePullSecretsPath+"/"+imagePullSecretName, nil, nil)
	if err != nil {
		return err
	}
	return nil
}
