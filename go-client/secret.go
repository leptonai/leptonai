package goclient

import (
	"encoding/json"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/k8s/secret"
)

type Secret struct {
	Lepton
}

func (s *Secret) Create(secrets []secret.SecretItem) error {
	body, err := json.Marshal(secrets)
	if err != nil {
		return err
	}
	header := map[string]string{
		"Content-Type": "application/json",
	}
	_, err = s.HTTP.RequestPath(http.MethodPost, "/secrets", header, body)
	if err != nil {
		return err
	}
	return nil
}

func (s *Secret) List() ([]string, error) {
	output, err := s.HTTP.RequestPath(http.MethodGet, "/secrets", nil, nil)
	if err != nil {
		return nil, err
	}
	ret := []string{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}

func (s *Secret) Delete(name string) error {
	_, err := s.HTTP.RequestPath(http.MethodDelete, "/secrets/"+name, nil, nil)
	if err != nil {
		return err
	}
	return nil
}
