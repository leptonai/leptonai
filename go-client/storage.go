package goclient

import (
	"bytes"
	"encoding/json"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/leptonai/lepton/go-pkg/util"
)

const storagePath = "/storage/default"
const duPath = "/storage/du"

type Storage struct {
	Lepton
}

func (s *Storage) Ls(filePath string) ([]map[string]string, error) {
	fullPath := filepath.Join(storagePath, filePath)
	output, err := s.http.RequestPath(http.MethodGet, fullPath, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := []map[string]string{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}

func (s *Storage) TotalDiskUsageBytes() (int, error) {
	output, err := s.http.RequestPath(http.MethodGet, duPath, nil, nil)
	if err != nil {
		return 0, err
	}
	ret := map[string]int{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return 0, err
	}
	return ret["TotalDiskUsage"], nil
}

func (s *Storage) Mkdir(filePath string) error {
	fullPath := filepath.Join(storagePath, filePath)
	_, err := s.http.RequestPath(http.MethodPut, fullPath, nil, nil)
	if err != nil {
		return err
	}
	return nil
}

func (s *Storage) PathExists(filePath string) bool {
	fullPath := filepath.Join(storagePath, filePath)
	_, err := s.http.RequestPath(http.MethodHead, fullPath, nil, nil)
	// HTTP.RequestPath returns error if the status code is not 2xx
	return err == nil
}

func (s *Storage) Rm(filePath string) error {
	fullPath := filepath.Join(storagePath, filePath)
	_, err := s.http.RequestPath(http.MethodDelete, fullPath, nil, nil)
	if err != nil {
		return err
	}

	return nil
}

func (s *Storage) Upload(absLocalFilePath string, remotePath string) error {
	fullPath := filepath.Join(storagePath, remotePath)
	form := map[string]string{"file": "@" + absLocalFilePath}
	ct, body, err := createForm(form)
	if err != nil {
		return err
	}

	ct_header := map[string]string{"Content-Type": ct}

	_, err = s.http.RequestPath(http.MethodPost, fullPath, ct_header, body)
	if err != nil {
		return err
	}
	return nil
}

func (s *Storage) Download(remoteFilePath string, absLocalFilePath string) error {
	fullPath := filepath.Join(storagePath, remoteFilePath)
	body, err := s.http.RequestPath(http.MethodGet, fullPath, nil, nil)
	if err != nil {
		return err
	}
	r := bytes.NewReader(body)
	err = util.CreateAndCopy(absLocalFilePath, r)
	if err != nil {
		return err
	}
	return nil
}

func createForm(form map[string]string) (string, []byte, error) {
	body := new(bytes.Buffer)
	mp := multipart.NewWriter(body)
	defer mp.Close()
	for key, val := range form {
		if strings.HasPrefix(val, "@") {
			val = val[1:]
			file, err := os.Open(val)
			if err != nil {
				return "", nil, err
			}
			defer file.Close()
			part, err := mp.CreateFormFile(key, val)
			if err != nil {
				return "", nil, err
			}
			_, err = io.Copy(part, file)
			if err != nil {
				return "", nil, err
			}
		} else {
			err := mp.WriteField(key, val)
			if err != nil {
				return "", nil, err
			}
		}
	}
	ct := mp.FormDataContentType()
	err := mp.Close()
	if err != nil {
		return "", nil, err
	}
	return ct, body.Bytes(), nil
}
