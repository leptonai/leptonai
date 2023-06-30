package e2etests

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/leptonai/lepton/go-pkg/util"
)

const (
	lsEmptyMsg  = "0 directories, 0 files"
	mkDirMsg    = "Created directory"
	rmMsg       = "Deleted"
	uploadMsg   = "Uploaded file"
	downloadMsg = "Downloaded file"
)

func TestCLIStorageListEmpty(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	newDir := newName(t.Name())
	err = lepton.Storage().Mkdir(newDir)
	if err != nil {
		t.Fatalf("Failed to make new directory %s : %s", newDir, err)
	}
	fullArgs := []string{"storage", "ls", newDir}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatalf("Storage ls %s failed with output %s: %s", newDir, output, err)
	}
	if !strings.Contains(output, lsEmptyMsg) {
		t.Fatalf("Expected output to contain %s, got '%s'", lsEmptyMsg, output)
	}
}

func TestCLIStorageListNonExistent(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	nonExistent := newName(t.Name())
	fullArgs := []string{"storage", "ls", "nonExistent"}
	output, err = client.Run(fullArgs...)
	if err == nil {
		t.Fatalf("Expected error since path %s does not exist, got %s", nonExistent, output)
	}
}

func TestCLIStorageMkdir(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	testDir := newName(t.Name())
	fullArgs := []string{"storage", "mkdir", testDir}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatal("Storage mkdir failed.", output, err)
	}
	if !strings.Contains(output, mkDirMsg+" "+testDir) {
		t.Fatalf("Expected output to contain %s, got '%s'", mkDirMsg+" "+testDir, output)
	}
	rootContents, err := lepton.Storage().Ls("/")
	if err != nil {
		t.Fatal("Storage ls failed.", err)
	}
	if len(rootContents) < 1 {
		t.Fatalf("Expected root to contain at least 1 item, got %d", len(rootContents))
	}
	for _, item := range rootContents {
		if item["name"] == testDir {
			return
		}
	}
	t.Fatalf("Expected root to contain %s, got %v", testDir, rootContents)
}

func TestCLIStorageUpload(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	testFileName := newName(t.Name())
	testFilePath := filepath.Join(leptonCacheDir, testFileName)
	file, err := os.Create(testFilePath)
	if err != nil {
		t.Fatalf("Failed to create file %s: %s", testFilePath, err)
	}
	_, err = file.Write([]byte("hello world"))
	if err != nil {
		t.Fatalf("Failed to write to file %s: %s", testFilePath, err)
	}

	err = file.Close()
	if err != nil {
		t.Fatalf("Failed to close file %s: %s", testFilePath, err)
	}

	fullArgs := []string{"storage", "upload", testFilePath, "/"}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatalf("Storage upload %s failed with output %s: %s", testFilePath, output, err)
	}
	expected := uploadMsg + " " + testFilePath
	if !strings.Contains(output, expected) {
		t.Fatalf("Expected output to contain %s, got '%s'", expected, output)
	}

	pathExists := lepton.Storage().PathExists("/" + testFileName)
	if !pathExists {
		t.Fatalf("Expected file %s to be uploaded, but it does not exist", testFileName)
	}
}

func TestCLIStorageRemoveFile(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	testFileName := newName(t.Name())
	testFilePath := filepath.Join(leptonCacheDir, testFileName)
	file, err := os.Create(testFilePath)
	if err != nil {
		t.Fatalf("Failed to create file %s: %s", testFilePath, err)
	}
	_, err = file.Write([]byte("hello world"))
	if err != nil {
		t.Fatalf("Failed to write to file %s: %s", testFilePath, err)
	}
	err = file.Close()
	if err != nil {
		t.Fatalf("Failed to close file %s: %s", testFilePath, err)
	}

	err = lepton.Storage().Upload(testFilePath, "/"+testFileName)
	if err != nil {
		t.Fatalf("Failed to upload file %s: %s", testFilePath, err)
	}
	fullArgs := []string{"storage", "rm", testFileName}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatalf("Storage rm %s failed with output %s: %s", testFileName, output, err)
	}
	expected := rmMsg + " " + testFileName
	if !strings.Contains(output, expected) {
		t.Fatalf("Expected output to contain %s, got '%s'", expected, output)
	}

	pathExists := lepton.Storage().PathExists("/" + testFileName)
	if pathExists {
		t.Fatalf("Expected file %s to be deleted, but it still exists", testFileName)
	}
}

func TestCLIStorageRmdir(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	testDirName := newName(t.Name())
	err = lepton.Storage().Mkdir("/" + testDirName)
	if err != nil {
		t.Fatalf("Failed to create directory %s: %s", testDirName, err)
	}
	fullArgs := []string{"storage", "rmdir", testDirName}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatalf("Storage rmdir %s failed with output %s: %s", testDirName, output, err)
	}
	expected := rmMsg + " " + testDirName
	if !strings.Contains(output, expected) {
		t.Fatalf("Expected output to contain %s, got '%s'", expected, output)
	}

	pathExists := lepton.Storage().PathExists("/" + testDirName)
	if pathExists {
		t.Fatalf("Expected directory %s to be removed, but it still exists", testDirName)
	}
}

func TestCLIStorageDownload(t *testing.T) {
	output, err := client.Login("")
	if err != nil {
		t.Fatal("Login failed", err, output)
	}
	testFileName := newName(t.Name())
	testFilePath := filepath.Join(leptonCacheDir, testFileName)
	file, err := os.Create(testFilePath)
	if err != nil {
		t.Fatalf("Failed to create file %s: %s", testFilePath, err)
	}
	_, err = file.Write([]byte(testFileName + "hello world"))
	if err != nil {
		t.Fatalf("Failed to write to file %s: %s", testFilePath, err)
	}
	err = file.Close()
	if err != nil {
		t.Fatalf("Failed to close file %s: %s", testFilePath, err)
	}

	err = lepton.Storage().Upload(testFilePath, "/"+testFileName)
	if err != nil {
		t.Fatalf("Failed to upload file %s: %s", testFilePath, err)
	}
	downloadPath := filepath.Join(leptonCacheDir, testFileName+"-downloaded")

	fullArgs := []string{"storage", "download", "/" + testFileName, downloadPath}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatalf("Storage download %s failed with output %s: %s", testFileName, output, err)
	}
	expected := downloadMsg + " /" + testFileName
	if !strings.Contains(output, expected) {
		t.Fatalf("Expected output to contain %s, got '%s'", expected, output)
	}

	equals := util.DeepCompareEq(testFilePath, downloadPath)
	if !equals {
		t.Fatalf("Expected downloaded file %s to equal uploaded file %s", downloadPath, testFilePath)
	}
}
