package httpapi

import (
	"log"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/lepton-mothership/cell"
	crdv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

func HandleCellGet(c *gin.Context) {
	cl, err := cell.Get(c.Param("cename"))
	if err != nil {
		log.Println("failed to get cell:", err)
		// TODO: check if cell not found and return user error if not found
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get cell: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, cl)
}

func HandleCellList(c *gin.Context) {
	cls, err := cell.List()
	if err != nil {
		log.Println("failed to list cells:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to list cells: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, cls)
}

func HandleCellCreate(c *gin.Context) {
	var spec crdv1alpha1.LeptonCellSpec
	err := c.BindJSON(&spec)
	if err != nil {
		log.Println("failed to bind json:", err)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to get cell: " + err.Error()})
		return
	}

	cl, err := cell.Create(spec)
	if err != nil {
		log.Println("failed to create cell:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create cell: " + err.Error()})
		return
	}

	c.JSON(http.StatusCreated, cl)
}

func HandleCellDelete(c *gin.Context) {
	err := cell.Delete(c.Param("cename"), false)
	if err != nil {
		log.Println("failed to delete cell:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete cell: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}

func HandleCellUpdate(c *gin.Context) {
	var spec crdv1alpha1.LeptonCellSpec
	err := c.BindJSON(&spec)
	if err != nil {
		log.Println("failed to bind json:", err)
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to get cell: " + err.Error()})
		return
	}

	cl, err := cell.Update(spec)
	if err != nil {
		log.Println("failed to update cell:", err)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to update cell: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, cl)
}
