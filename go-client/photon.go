package goclient

import (
	"bytes"
	"encoding/json"
	"io"
	"mime/multipart"
	"net/http"
	"os"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
)

const photonsPath = "/photons"

type Photon struct {
	Lepton
}

func (l *Photon) Push(filename, photonName string) (*httpapi.Photon, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	formFile, err := writer.CreateFormFile("file", filename)
	if err != nil {
		return nil, err
	}
	_, err = io.Copy(formFile, file)
	if err != nil {
		return nil, err
	}
	if err := writer.Close(); err != nil {
		return nil, err
	}

	header := map[string]string{
		"Content-Type": writer.FormDataContentType(),
	}

	output, err := l.HTTP.RequestPath(http.MethodPost, photonsPath, header, body.Bytes())
	if err != nil {
		return nil, err
	}
	ret := &httpapi.Photon{}
	if err := json.Unmarshal(output, ret); err != nil {
		return nil, err
	}
	return ret, nil
}

func (l *Photon) List() ([]httpapi.Photon, error) {
	output, err := l.HTTP.RequestPath(http.MethodGet, photonsPath, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := []httpapi.Photon{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}

func (l *Photon) GetByName(photonName string) ([]httpapi.Photon, error) {
	output, err := l.HTTP.RequestPath(http.MethodGet, photonsPath+"?name="+photonName, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := []httpapi.Photon{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}

func (l *Photon) GetByID(photonID string) (*httpapi.Photon, error) {
	output, err := l.HTTP.RequestPath(http.MethodGet, photonsPath+"/"+photonID, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := &httpapi.Photon{}
	if err := json.Unmarshal(output, ret); err != nil {
		return nil, err
	}
	return ret, nil
}

func (l *Photon) Delete(photonID string) error {
	_, err := l.HTTP.RequestPath(http.MethodDelete, photonsPath+"/"+photonID, nil, nil)
	if err != nil {
		return err
	}
	return nil
}
