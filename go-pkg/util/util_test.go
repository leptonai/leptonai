package util

import (
	"errors"
	"log"
	"math/rand"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

func TestRandString(t *testing.T) {
	result := RandString(10)
	if len(result) != 10 {
		t.Errorf("RandString(10) = %s; want length 10", result)
	}
}

func TestContainsString(t *testing.T) {
	slice := []string{"a", "b", "c"}
	if !ContainsString(slice, "a") {
		t.Errorf("ContainsString(slice, \"a\") = false; want true")
	}
	if ContainsString(slice, "d") {
		t.Errorf("ContainsString(slice, \"d\") = true; want false")
	}
}

func TestRemoveString(t *testing.T) {
	slice := []string{"a", "b", "c"}
	result, ok := RemoveString(slice, "a")
	if !ok {
		t.Errorf("RemoveString(slice, \"a\") = %v; want true", ok)
	}
	if ContainsString(result, "a") {
		t.Errorf("RemoveString(slice, \"a\") = %v; want not contain \"a\"", result)
	}
	if len(result) != 2 {
		t.Errorf("RemoveString(slice, \"a\") = %v; want length 2", result)
	}
}

func TestRemoveEmptyString(t *testing.T) {
	tt := []struct {
		input    []string
		expected []string
	}{
		{
			input:    []string{"a", "b", "c"},
			expected: []string{"a", "b", "c"},
		},
		{
			input:    []string{"a", "", "c"},
			expected: []string{"a", "c"},
		},
		{
			input:    []string{"a", "b", "", "", ""},
			expected: []string{"a", "b"},
		},
		{
			input:    []string{""},
			expected: nil,
		},
		{
			input:    []string{"", ""},
			expected: nil,
		},
	}
	for i, tv := range tt {
		result := RemoveEmptyStringFromSlice(tv.input)
		if !reflect.DeepEqual(result, tv.expected) {
			t.Errorf("#%d: RemoveEmptyString(%v) = %v; want %v", i, tv.input, result, tv.expected)
		}
	}
}

func TestUniqStringSlice(t *testing.T) {
	slice := []string{"a", "b", "c", "a", "b", "c"}
	result := UniqStringSlice(slice)
	if len(result) != 3 {
		t.Errorf("UniqStringSlice(slice) = %v; want length 3", result)
	}
}

func TestRemovePrefix(t *testing.T) {
	pre := "l33t"
	msg := ""
	expected := ""
	for i := 0; i < 10; i++ {
		word := RandString(10)
		expected += word + " "
		if rand.Intn(3) == 0 {
			word = pre + word
		}
		msg += word + " "
	}
	result := RemovePrefix(msg, pre)
	if result != expected {
		t.Errorf("RemovePrefix(%s, %s) = %s; want %s", msg, pre, result, expected)
	}
}

func TestCheckPathExists(t *testing.T) {
	newPath := "/tmp/" + RandString(10) + "/" + RandString(10)
	exists, err := CheckPathExists(newPath)
	if err != nil {
		t.Errorf("CheckPathExists(%s) = %v; want nil", newPath, err)
	}
	if exists {
		t.Errorf("CheckPathExists(%s) = true; want false", newPath)
	}
	err = os.MkdirAll(newPath, 0777)
	if err != nil {
		log.Fatal(err)
	}
	exists, err = CheckPathExists(newPath)
	if err != nil {
		t.Errorf("CheckPathExists(%s) = %v; want nil", newPath, err)
	}
	if !exists {
		t.Errorf("CheckPathExists(%s) = false; want true", newPath)
	}
}

func TestCheckPathIsExistingDir(t *testing.T) {
	newPath := "/tmp/" + RandString(10) + "/" + RandString(10)
	isDir, err := CheckPathIsExistingDir(newPath)
	if err == nil {
		t.Errorf("CheckPathIsExistingDir(%s) = nil; want error", newPath)
	}
	if isDir {
		t.Errorf("CheckPathIsExistingDir(%s) = true; want false", newPath)
	}

	err = os.MkdirAll(newPath, 0777)
	if err != nil {
		log.Fatal(err)
	}

	isDir, err = CheckPathIsExistingDir(newPath)
	if err != nil {
		t.Errorf("CheckPathIsExistingDir(%s) = %v; want nil", newPath, err)
	}
	if !isDir {
		t.Errorf("CheckPathIsExistingDir(%s) = false; want true", newPath)
	}
	fileName := "file-" + RandString(10)
	filePath := newPath + fileName
	file, err := os.Create(filePath)
	if err != nil {
		t.Errorf("could not create file at %s: %v", filePath, err)
	}
	defer file.Close()
	isDir, err = CheckPathIsExistingDir(filePath)
	if err != nil {
		t.Errorf("CheckPathIsExistingDir(%s) = %v; want nil", filePath, err)
	}
	if isDir {
		t.Errorf("CheckPathIsExistingDir(%s) = true; want false", filePath)
	}
}

func TestCreateAndCopy(t *testing.T) {
	originalFilePath := "/tmp/" + RandString(10) + "/" + RandString(10) + "file-" + RandString(10)
	err := os.MkdirAll(filepath.Dir(originalFilePath), 0777)
	if err != nil {
		log.Fatal(err)
	}
	originalFile, err := os.Create(originalFilePath)
	if err != nil {
		t.Errorf("could not create file at %s: %v", originalFilePath, err)
	}
	defer originalFile.Close()

	newFilePath := "/tmp/" + RandString(10) + "/" + RandString(10) + "file-" + RandString(10)
	err = os.MkdirAll(filepath.Dir(newFilePath), 0777)
	if err != nil {
		log.Fatal(err)
	}
	err = CreateAndCopy(newFilePath, originalFile)
	if err != nil {
		log.Fatal(err)
	}
	if err != nil {
		t.Errorf("CreateAndCopy(%s, %s) = %v; want nil", newFilePath, originalFilePath, err)
	}
	if !DeepCompareEq(originalFilePath, newFilePath) {
		t.Errorf("Files %s and %s are not equal", originalFilePath, newFilePath)
	}
}

func TestEvalPath(t *testing.T) {
	mountPath := "/tmp/" + RandString(10) + "/" + RandString(10)
	subPath := mountPath + "/../.."
	validPath, err := IsSubPath(mountPath, subPath)
	if err != nil {
		log.Fatal(err)
	}
	if validPath {
		t.Errorf("EvalPath(%s, %s) = true; want false", mountPath, subPath)
	}
	subPath2 := mountPath + "/" + RandString(10)
	validPath, err = IsSubPath(mountPath, subPath2)
	if err != nil {
		t.Errorf("EvalPath(%s, %s) = %v; want nil", mountPath, subPath2, err)
	}
	if !validPath {
		t.Errorf("EvalPath(%s, %s) = false; want true", mountPath, subPath2)
	}
}

func TestIsEmpty(t *testing.T) {
	newPath := "/tmp/" + RandString(10) + "/" + RandString(10)
	err := os.MkdirAll(newPath, 0777)
	if err != nil {
		log.Fatal(err)
	}
	isEmpty, err := IsEmptyDir(newPath)
	if err != nil {
		t.Errorf("IsEmpty(%s) = %v; want nil", newPath, err)
	}
	if !isEmpty {
		t.Errorf("IsEmpty(%s) = false; want true", newPath)
	}
	newFile, err := os.Create(newPath + "/" + RandString(10))
	if err != nil {
		t.Errorf("could not create file at %s: %v", newPath, err)
	}
	defer newFile.Close()
	isEmpty, err = IsEmptyDir(newPath)
	if err != nil {
		t.Errorf("IsEmpty(%s) = %v; want nil", newPath, err)
	}
	if isEmpty {
		t.Errorf("IsEmpty(%s) = true; want false", newPath)
	}
}

func TestDu(t *testing.T) {
	mntPath := "/tmp/" + RandString(10)
	err := os.MkdirAll(mntPath, 0777)
	if err != nil {
		log.Fatal(err)
	}

	_, err = Du(mntPath)
	if err != nil {
		t.Errorf("Du(%s) threw error: %v", mntPath, err)
	}

	flags := []string{"-s", "-h", "-c", "-k"}
	for _, flag := range flags {
		_, err := Du(flag, mntPath)
		if err != nil {
			t.Errorf("Du(%s %s) threw error: %v", mntPath, flag, err)
		}
	}

	stdout, err := Du("-s", mntPath)
	if err != nil {
		t.Errorf("Du(%s -s) threw error: %v", mntPath, err)
	}
	if !strings.Contains(stdout, mntPath) {
		t.Errorf("Du(%s -s) = %s; want it to contain %s", mntPath, stdout, mntPath)
	}
}

func TestTotalDuDir(t *testing.T) {
	mntPath := "/tmp/" + RandString(10)
	err := os.MkdirAll(mntPath, 0777)
	if err != nil {
		log.Fatal(err)
	}
	// create a 1 MB file
	file, err := os.Create(mntPath + "/" + RandString(10))
	if err != nil {
		t.Errorf("could not create file at %s: %v", mntPath, err)
	}
	defer file.Close()
	_, err = file.Write(make([]byte, 1024*1024))
	if err != nil {
		t.Errorf("could not write to file at %s: %v", mntPath, err)
	}

	sizeBytes, err := TotalDirDiskUsageBytes(mntPath)
	if err != nil {
		t.Errorf("TotalDirDiskUsageKB(%s) threw error: %v", mntPath, err)
	}
	sizeDiff := sizeBytes - 1024*1024
	if sizeDiff < 0 {
		sizeDiff = -1 * sizeDiff
	}
	if sizeDiff > 5*1024 {
		t.Errorf("got size %d bytes, want within 5 kb of %d bytes", sizeBytes, 1024)
	}
}

func TestRetry(t *testing.T) {
	err := Retry(3, 1*time.Second, func() error {
		return nil
	})
	if err != nil {
		t.Errorf("Retry() = %v; want nil", err)
	}
	err = Retry(3, 1*time.Second, func() error {
		return errors.New("test")
	})
	if err == nil {
		t.Errorf("Retry() = nil; want error")
	}
}

func TestUpdateImageTag(t *testing.T) {
	tests := []struct {
		image  string
		tag    string
		output string
	}{
		{"gcr.io/google_containers/pause-amd64:3.0", "3.1", "gcr.io/google_containers/pause-amd64:3.1"},
		{"gcr.io/google_containers/pause-amd64:3.0", "3.0", "gcr.io/google_containers/pause-amd64:3.0"},
	}
	for _, test := range tests {
		newImage := UpdateImageTag(test.image, test.tag)
		if newImage != test.output {
			t.Errorf("UpdateImageTag(%s, %s) = %s; want %s", test.image, test.tag, newImage, test.output)
		}
	}
}

func TestValidateEnvName(t *testing.T) {
	tests := []struct {
		name  string
		valid bool
	}{
		{"lepton", true},
		{"lepton_", false},
		{"LEPTON", true},
		{"LEPTON_", false},
		{"lepton_test", false},
		{"LEPTON_TEST", false},
		{"lepton_test_", false},
		{"LEPTON_TEST_", false},
		{"LepTON_TEST_", false},
		{"PHOTON_TEST", true},
	}
	for _, test := range tests {
		valid := ValidateEnvName(test.name)
		if valid != test.valid {
			t.Errorf("ValidateEnvName(%s) = %v; want %v", test.name, valid, test.valid)
		}
	}
}

func TestMaskIPAddress(t *testing.T) {
	tests := []struct {
		input  string
		output string
	}{
		{
			"Readiness probe failed: dial tcp 10.0.37.1:8080: connect: connection refused",
			"Readiness probe failed: dial tcp port 8080: connect: connection refused",
		},
	}
	for _, test := range tests {
		output := MaskIPAddressInReadinessProbeMessage(test.input)
		if output != test.output {
			t.Errorf("MaskIPAddress(%s) = %s; want %s", test.input, output, test.output)
		}
	}

}
