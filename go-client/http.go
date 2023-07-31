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
	Header        http.Header
}

func newHeader(authToken string) http.Header {
	header := http.Header{}
	if authToken != "" {
		header.Set("Authorization", "Bearer "+authToken)
	}
	return header
}

func NewHTTP(remoteURL string, authToken string) *HTTP {
	return &HTTP{
		RemoteURL:     remoteURL,
		Header:        newHeader(authToken),
		SkipVerifyTLS: false,
	}
}

func NewHTTPSkipVerifyTLS(remoteURL string, authToken string) *HTTP {
	return &HTTP{
		RemoteURL:     remoteURL,
		Header:        newHeader(authToken),
		SkipVerifyTLS: true,
	}
}

func (h *HTTP) RequestURL(method, url string, headers map[string]string, data []byte) ([]byte, error) {
	return h.RequestURLUntil(method, url, headers, data, 0, 0)
}

func (h *HTTP) RequestURLUntil(method, url string, headers map[string]string, data []byte, expectedBytes, timeoutInSeconds int) ([]byte, error) {
	var reader *bytes.Reader
	if data != nil {
		reader = bytes.NewReader(data)
	} else {
		reader = bytes.NewReader([]byte{})
	}
	req, err := http.NewRequest(method, url, reader)
	if err != nil {
		return nil, err
	}
	req.Header = h.Header.Clone()
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	if timeoutInSeconds == 0 {
		timeoutInSeconds = 30
	}
	httpClient := &http.Client{
		Timeout: time.Duration(timeoutInSeconds) * time.Second,
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

	if expectedBytes > 0 {
		buf := make([]byte, expectedBytes)
		pos := 0
		for {
			n, err := resp.Body.Read(buf[pos:expectedBytes])
			pos += n
			if err != nil {
				if err == io.EOF {
					break
				}
				return buf[:pos], err
			}
			if pos >= expectedBytes {
				break
			}
		}
		return buf[:pos], nil
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if !(200 <= resp.StatusCode && resp.StatusCode < 300) {
		return nil, fmt.Errorf("unexpected HTTP status code %v with body %s", resp.StatusCode, string(body))
	}
	return body, nil
}

func (h *HTTP) RequestPath(method, path string, headers map[string]string, data []byte) ([]byte, error) {
	url := h.RemoteURL + path
	return h.RequestURL(method, url, headers, data)
}
