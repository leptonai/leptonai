package goclient

import (
	"bytes"
	"crypto/tls"
	"fmt"
	"io"
	"net/http"
	"time"
)

type HTTP struct {
	RemoteURL     string
	SkipVerifyTLS bool
}

func NewHTTP(remoteURL string) *HTTP {
	return &HTTP{
		RemoteURL:     remoteURL,
		SkipVerifyTLS: false,
	}
}

func NewHTTPSkipVerifyTLS(remoteURL string) *HTTP {
	return &HTTP{
		RemoteURL:     remoteURL,
		SkipVerifyTLS: true,
	}
}

func (h *HTTP) Request(method, path string, headers map[string]string, data []byte) ([]byte, error) {
	var reader *bytes.Reader
	if data != nil {
		reader = bytes.NewReader(data)
	} else {
		reader = bytes.NewReader([]byte{})
	}
	url := h.RemoteURL + path
	req, err := http.NewRequest(method, url, reader)
	if err != nil {
		return nil, err
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	httpClient := &http.Client{
		Timeout: time.Duration(60 * time.Second),
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: h.SkipVerifyTLS,
			},
		},
	}

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected HTTP status code %v with body %s", resp.StatusCode, string(body))
	}
	return body, nil
}
