package util

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

func CheckPathExists(path string) (bool, error) {
	_, err := os.Stat(path)
	if os.IsNotExist(err) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return true, nil
}

func CheckPathIsExistingDir(absPath string) (bool, error) {
	stat, err := os.Stat(absPath)
	if os.IsNotExist(err) {
		return false, fmt.Errorf("path %s does not exist", absPath)
	}
	if err != nil {
		return false, err
	}
	if !stat.IsDir() {
		return false, nil
	}
	return true, nil
}

// CreateAndCopy creates a new file at filepath and copies the content of the reader to it
func CreateAndCopy(filePath string, r io.Reader) error {
	newFile, err := os.Create(filePath)
	if err != nil {
		return err
	}
	defer newFile.Close()

	_, err = io.Copy(newFile, r)
	if err != nil {
		return err
	}
	return nil
}

func IsSubPath(mountPath string, subpath string) (bool, error) {
	up := ".." + string(os.PathSeparator)
	path, err := filepath.Abs(subpath)
	if err != nil {
		return false, err
	}
	rel, err := filepath.Rel(mountPath, path)
	if err != nil {
		return false, err
	}
	if !strings.HasPrefix(rel, up) && rel != ".." {
		return true, nil
	}
	return false, nil
}

func IsEmptyDir(name string) (bool, error) {
	f, err := os.Open(name)
	if err != nil {
		return false, err
	}
	defer f.Close()
	_, err = f.Readdir(1)
	if err == io.EOF {
		return true, nil
	}
	return false, err
}

// wrapper for du command
func Du(args ...string) (string, error) {
	cmd := exec.Command("du", args...)
	out, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return string(out), nil
}

// note: -b flag not supported by macOS
func TotalDirDiskUsageBytes(dirPath string) (int, error) {
	stdout, err := Du("-sb", dirPath)
	if err != nil {
		return 0, err
	}

	stdout = strings.TrimSuffix(stdout, "\n")
	stdout = strings.TrimSuffix(stdout, dirPath)
	stdout = strings.TrimSpace(stdout)
	size, err := strconv.Atoi(stdout)
	if err != nil {
		return 0, err
	}
	return size, nil
}
