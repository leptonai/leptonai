package httpapi

import (
	"bytes"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"testing"

	"github.com/leptonai/lepton/go-pkg/util"
)

const (
	apiPath = "/api/v1/storage/default/"
)

func TestStorageCheckExists(t *testing.T) {
	testDir, err := makeTestDir(mountPath, t.Name())
	if err != nil {
		t.Errorf("Error creating test path: %s", err)
	}
	relTestDir := filepath.Base(testDir)

	err = makeFilesAndDirs(testDir)
	if err != nil {
		t.Errorf("Error creating test files and dirs: %s", err)
	}

	toTest := []string{"file-0", "file-1", "file-2", "dir-0", "dir-1", "dir-2"}
	for _, f := range toTest {
		url := filepath.Join(apiPath, relTestDir, f)
		req, _ := http.NewRequest("HEAD", url, nil)
		w := httptest.NewRecorder()

		r.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Response code is %v", w.Code)
		}
	}
	doesNotExist := []string{"file-3", "dir-3"}
	for _, f := range doesNotExist {
		url := filepath.Join(apiPath, relTestDir, f)
		req, _ := http.NewRequest("HEAD", url, nil)
		w := httptest.NewRecorder()

		r.ServeHTTP(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("Response code is %v", w.Code)
		}
	}
}

func TestStorageGetDir(t *testing.T) {
	testDir, err := makeTestDir(mountPath, t.Name())
	if err != nil {
		t.Errorf("Error creating test path: %s", err)
	}
	err = makeFilesAndDirs(testDir)
	if err != nil {
		t.Errorf("Error creating test files and dirs: %s", err)
	}

	relTestDir := filepath.Base(testDir)
	url := filepath.Join(apiPath, relTestDir)
	req, _ := http.NewRequest("GET", url, nil)
	w := httptest.NewRecorder()

	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Response code is %v", w.Code)
	}

	responseData, _ := io.ReadAll(w.Body)
	var data []map[string]interface{}
	err = json.Unmarshal(responseData, &data)
	if err != nil {
		t.Errorf("Error decoding response body")
	}
	if len(data) != 6 {
		t.Errorf("Expected 6 entries, got %v", len(data))
	}
}

func TestStorageMakeDir(t *testing.T) {
	testDir, err := makeTestDir(mountPath, t.Name())
	if err != nil {
		t.Errorf("Error creating test path: %s", err)
	}
	relTestDir := filepath.Base(testDir)
	createNewDir := "test-dir-" + util.RandString(5)
	url := filepath.Join(apiPath, relTestDir, createNewDir)

	req, _ := http.NewRequest("PUT", url, nil)
	w := httptest.NewRecorder()

	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("Response code is %v", w.Code)
	}

	exists, err := util.CheckPathIsExistingDir(filepath.Join(testDir, createNewDir))
	if err != nil {
		t.Errorf("Error checking if path exists: %s", err)
	}
	if !exists {
		t.Errorf("Expected path to exist and to be a directory")
	}
}

func TestStorageUploadFile(t *testing.T) {
	testDir, err := makeTestDir(mountPath, t.Name())
	if err != nil {
		t.Errorf("Error creating test path: %s", err)
	}
	relTestDir := filepath.Base(testDir)

	localTestFile := "test-file-" + util.RandString(5)
	remoteTestFile := filepath.Join(testDir, localTestFile)

	// create testfile with random data
	err = writeRandomDataToFile(localTestFile, 1024)
	if err != nil {
		t.Errorf("Error writing random data to file: %s", err)
	}
	defer os.Remove(localTestFile)

	f, err := os.Open(localTestFile)
	if err != nil {
		t.Errorf("Error opening file: %s", err)
	}
	defer f.Close()

	// create multipart form
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, err := writer.CreateFormFile("file", localTestFile)

	if err != nil {
		t.Errorf("Error creating form file: %s", err)
	}
	_, err = io.Copy(part, f)
	if err != nil {
		t.Errorf("Error copying file to form file: %s", err)
	}
	err = writer.Close()
	if err != nil {
		t.Errorf("Error closing writer: %s", err)
	}

	url := filepath.Join(apiPath, relTestDir, localTestFile)
	req, _ := http.NewRequest("POST", url, body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	w := httptest.NewRecorder()

	r.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Errorf("Response code is %v", w.Code)
	}

	exists, err := util.CheckPathExists(remoteTestFile)
	if err != nil {
		t.Errorf("Error checking if path exists")
	}
	if !exists {
		t.Errorf("Expected file %s to exist", remoteTestFile)
	}

	if !util.DeepCompareEq(remoteTestFile, localTestFile) {
		t.Errorf("Expected file %s to be equal to %s", remoteTestFile, localTestFile)
	}
}

func TestStorageDownloadFile(t *testing.T) {
	testDir, err := makeTestDir(mountPath, t.Name())
	if err != nil {
		t.Errorf("Error creating test dir: %s", err)
	}
	relTestDir := filepath.Base(testDir)

	fileToDownload := filepath.Join(testDir, "testfile")
	err = writeRandomDataToFile(fileToDownload, 1024)
	if err != nil {
		t.Errorf("Error writing random data to file: %s", err)
	}

	url := filepath.Join(apiPath, relTestDir, filepath.Base(fileToDownload))
	req, _ := http.NewRequest("GET", url, nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Response code is %v", w.Code)
	}

	downloadedFile := "test-downloaded-file-" + util.RandString(5)
	defer os.Remove(downloadedFile)

	out, err := os.Create(downloadedFile)
	if err != nil {
		t.Errorf("Error creating downloaded file: %s", err)
	}

	defer out.Close()

	_, err = io.Copy(out, w.Result().Body)
	if err != nil {
		t.Errorf("Error copying file to downloaded file: %s", err)
	}
	defer w.Result().Body.Close()

	if !util.DeepCompareEq(fileToDownload, downloadedFile) {
		t.Errorf("Expected file %s to be equal to %s", fileToDownload, downloadedFile)
	}
}
func TestStorageDelete(t *testing.T) {
	testDir, err := makeTestDir(mountPath, t.Name())
	if err != nil {
		t.Errorf("Error creating test dir: %s", err)
	}
	relTestDir := filepath.Base(testDir)
	err = makeFilesAndDirs(testDir)
	if err != nil {
		t.Errorf("Error making files and dirs: %s", err)
	}
	toDelete := []string{"file-0", "file-1", "file-2", "dir-0", "dir-1", "dir-2"}
	for _, f := range toDelete {
		url := filepath.Join(apiPath, relTestDir, f)
		req, _ := http.NewRequest("DELETE", url, nil)
		w := httptest.NewRecorder()

		r.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Response code is %v", w.Code)
		}

		exists, err := util.CheckPathExists(testDir + "/" + f)
		if err != nil {
			t.Errorf("Error checking if path exists")
		}
		if exists {
			t.Errorf("Expected file/directory %s to be deleted", f)
		}
	}
}

func writeRandomDataToFile(filePath string, size int) error {
	// Generate random data
	data := make([]byte, size)
	_, err := rand.Read(data)
	if err != nil {
		return fmt.Errorf("Error generating random data: %s", err)
	}

	// Write random data to the file
	file, err := os.Create(filePath)
	if err != nil {
		return fmt.Errorf("Error creating file: %s", err)
	}
	defer file.Close()

	_, err = file.Write(data)
	if err != nil {
		return fmt.Errorf("Error writing to file: %s", err)
	}
	return nil
}

func makeFilesAndDirs(dirPath string) error {
	// make 3 files and 3 dirs in dirPath
	for i := 0; i < 3; i++ {
		newDirPath := filepath.Join(dirPath, "dir-"+strconv.Itoa(i))
		err := os.MkdirAll(newDirPath, 0777)
		if err != nil {
			return err
		}
		newFilePath := filepath.Join(dirPath, "file-"+strconv.Itoa(i))
		_, err = os.Create(newFilePath)
		if err != nil {
			return err
		}
	}
	return nil
}

func makeTestDir(mountPath string, name string) (string, error) {
	testDir := mountPath + "/" + name + "-" + util.RandString(5) + "/"
	err := os.MkdirAll(testDir, 0777)
	if err != nil {
		return "", err
	}
	return testDir, nil
}
