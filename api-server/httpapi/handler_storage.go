package httpapi

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"github.com/gin-gonic/gin"
)

type StorageHandler struct {
	Handler
	mountPath string
}

type FileType string

type FileInfo struct {
	FileType FileType `json:"type"`
	Name     string   `json:"name"`
	AbsPath  string   `json:"path"`
}

const (
	Dir  FileType = "dir"
	File FileType = "file"
)

func NewStorageHandler(h Handler, mountPath string) *StorageHandler {
	mkdirErr := os.MkdirAll(mountPath, 0777)
	// Using 0777 as umask 022 is applied, resulting in 755 permissions
	// If path is already a directory, MkdirAll does nothing and returns nil.
	if mkdirErr != nil {
		goutil.Logger.Fatalw("failed to create mount path",
			"mountPath", mountPath,
			"error", mkdirErr,
		)
	}
	return &StorageHandler{
		Handler:   h,
		mountPath: mountPath,
	}
}

func (sh *StorageHandler) GetFileOrDir(c *gin.Context) {
	relPath := c.Param("path")
	absPath := filepath.Join(sh.mountPath, relPath)

	validPath, err := goutil.IsSubPath(sh.mountPath, absPath)
	if err != nil {
		goutil.Logger.Errorw("failed to check if path is subpath",
			"operation", "getStorageFileOrDir",
			"mountPath", sh.mountPath,
			"path", absPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}

	if !validPath {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "Provided path is not a valid subpath"})
		return
	}

	// check if the path exists, handle dir or file
	isDir, err := goutil.CheckPathIsExistingDir(absPath)
	if err != nil {
		goutil.Logger.Errorw("failed to check if path is existing dir",
			"operation", "getStorageFileOrDir",
			"path", absPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}
	if isDir {
		dirData, err := GetDirContents(absPath)
		if err != nil {
			goutil.Logger.Errorw("failed to get dir contents",
				"operation", "getStorageFileOrDir",
				"path", absPath,
				"error", err,
			)
			c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
			return
		}
		c.Header("Content-Type", "application/json")
		c.JSON(http.StatusOK, dirData)
	} else {
		filename := filepath.Base(absPath)
		c.Status(http.StatusOK)
		c.Header("Content-Description", "File Transfer")
		c.Header("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"", filename))
		c.Header("Content-Type", "application/octet-stream")
		c.File(absPath)
	}
}

// DiskUsage returns the total number of bytes stored in the filesystem
func (sh *StorageHandler) TotalDiskUsageBytes(c *gin.Context) {
	size, err := goutil.TotalDirDiskUsageBytes(sh.mountPath)
	if err != nil {
		goutil.Logger.Errorw("failed to get total disk usage",
			"operation", "totalDiskUsage",
			"mountPath", sh.mountPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.Header("Content-Type", "application/json")
	c.JSON(http.StatusOK, gin.H{"totalDiskUsageBytes": size})
}

func (sh *StorageHandler) CreateDir(c *gin.Context) {
	relPath := c.Param("path")
	absPath := filepath.Join(sh.mountPath, relPath)

	validPath, err := goutil.IsSubPath(sh.mountPath, absPath)
	if err != nil {
		goutil.Logger.Errorw("failed to check if path is subpath",
			"operation", "createDir",
			"path", relPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}
	if !validPath {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "Provided path is not a valid subpath"})
		return
	}

	err = os.MkdirAll(absPath, 0777)
	if err != nil {
		goutil.Logger.Errorw("failed to create directory",
			"operation", "createDir",
			"path", relPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}

	goutil.Logger.Infow("directory created",
		"operation", "createDir",
		"path", relPath,
	)
	c.JSON(http.StatusCreated, gin.H{"message": fmt.Sprintf("Directory '%s' created successfully", relPath)})
}

func (sh *StorageHandler) CreateFile(c *gin.Context) {
	relUploadPath := c.Param("path")
	absPath := filepath.Join(sh.mountPath, relUploadPath)

	validPath, err := goutil.IsSubPath(sh.mountPath, absPath)
	if err != nil {
		goutil.Logger.Errorw("failed to check if path is subpath",
			"operation", "createFile",
			"path", relUploadPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "error": sh.removeMountPathFromError(err)})
		return
	}
	if !validPath {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "Provided path is not a valid subpath"})
		return
	}

	dirPath := filepath.Dir(absPath)
	exists, err := goutil.CheckPathExists(dirPath)
	if err != nil {
		goutil.Logger.Errorw("failed to check if path exists",
			"operation", "createFile",
			"path", relUploadPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": fmt.Sprintf("Directory '%s' does not exist", filepath.Dir(relUploadPath))})
		return
	}

	// TODO: validate the request file type, size, etc.
	err = c.Request.ParseMultipartForm(32 << 20) // 32 MB of request body stored in memory, the rest temporarily on disk
	if err != nil {
		goutil.Logger.Errorw("failed to parse multipart form",
			"operation", "createFile",
			"path", relUploadPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}

	file, _, err := c.Request.FormFile("file")
	if err != nil {
		goutil.Logger.Errorw("failed to get file from request",
			"operation", "createFile",
			"path", relUploadPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}
	defer file.Close()
	filepath.Join(sh.mountPath, relUploadPath)
	err = goutil.CreateAndCopy(filepath.Join(sh.mountPath, relUploadPath), file)
	if err != nil {
		goutil.Logger.Errorw("failed to create and copy file",
			"operation", "createFile",
			"path", relUploadPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}

	goutil.Logger.Infow("file uploaded",
		"operation", "createFile",
		"path", relUploadPath,
	)
	c.JSON(http.StatusCreated, gin.H{"message": fmt.Sprintf("File '%s' uploaded successfully", relUploadPath)})
}

func (sh *StorageHandler) DeleteFileOrDir(c *gin.Context) {
	relPath := c.Param("path")
	absPath := filepath.Join(sh.mountPath, relPath)
	if absPath == sh.mountPath {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "Cannot delete root directory"})
		return
	}

	validPath, err := goutil.IsSubPath(sh.mountPath, absPath)
	if err != nil {
		goutil.Logger.Errorw("failed to check if path is subpath",
			"operation", "deleteFileOrDir",
			"path", relPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "error": sh.removeMountPathFromError(err)})
		return
	}
	if !validPath {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "Provided path is not a valid subpath"})
		return
	}

	// check if path is a directory, if so check if it is empty
	isDir, err := goutil.CheckPathIsExistingDir(absPath)
	if err != nil {
		goutil.Logger.Errorw("failed to check if path is directory",
			"operation", "deleteFileOrDir",
			"path", relPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}
	if isDir {
		IsEmptyDir, err := goutil.IsEmptyDir(absPath)
		if err != nil {
			goutil.Logger.Errorw("failed to check if directory is empty",
				"operation", "deleteFileOrDir",
				"path", relPath,
				"error", err,
			)
			c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
			return
		}
		if !IsEmptyDir {
			c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": fmt.Sprintf("Directory '%s' is not empty", relPath)})
			return
		}
	}
	// delete file or directory
	err = os.Remove(absPath)
	if err != nil {
		goutil.Logger.Errorw("failed to delete file or directory",
			"operation", "deleteFileOrDir",
			"path", relPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}

	if isDir {
		goutil.Logger.Infow("directory deleted",
			"operation", "deleteFileOrDir",
			"path", relPath,
		)
		c.JSON(http.StatusOK, gin.H{"message": fmt.Sprintf("Directory '%s' deleted successfully", relPath)})
	} else {
		goutil.Logger.Infow("file deleted",
			"operation", "deleteFileOrDir",
			"path", relPath,
		)
		c.JSON(http.StatusOK, gin.H{"message": fmt.Sprintf("File '%s' deleted successfully", relPath)})
	}
}

func (sh *StorageHandler) CheckExists(c *gin.Context) {
	relPath := c.Param("path")
	absPath := filepath.Join(sh.mountPath, relPath)

	validPath, err := goutil.IsSubPath(sh.mountPath, absPath)
	if err != nil {
		goutil.Logger.Errorw("failed to check if path is subpath",
			"operation", "checkExists",
			"path", relPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}
	if !validPath {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "Provided path is not a valid subpath"})
		return
	}

	exists, err := goutil.CheckPathExists(absPath)
	if err != nil {
		goutil.Logger.Errorw("failed to check if path exists",
			"operation", "checkExists",
			"path", relPath,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": sh.removeMountPathFromError(err)})
		return
	}
	if exists {
		c.JSON(http.StatusOK, gin.H{"message": fmt.Sprintf("Path '%s' exists", relPath)})
	} else {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": fmt.Sprintf("Path '%s' does not exist", relPath)})
	}
}

func (sh *StorageHandler) removeMountPathFromError(e error) string {
	return goutil.RemovePrefix(e.Error(), sh.mountPath)
}

func GetDirContents(absPath string) ([]FileInfo, error) {
	entries, err := os.ReadDir(absPath)
	if err != nil {
		return nil, err
	}
	// create json response
	dirData := []FileInfo{}
	for _, entry := range entries {
		entryType := File
		if entry.IsDir() {
			entryType = Dir
		}
		entryPath := filepath.Join(absPath, entry.Name())
		entryData := FileInfo{FileType: entryType, Name: entry.Name(), AbsPath: entryPath}
		dirData = append(dirData, entryData)
	}
	return dirData, nil
}
