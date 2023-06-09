package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
)

func deploymentPostHandler(c *gin.Context) {
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	ld := &leptonaiv1alpha1.LeptonDeployment{}

	if err := json.Unmarshal(body, &ld.Spec.LeptonDeploymentUserSpec); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if err := validateDeploymentInput(&ld.Spec.LeptonDeploymentUserSpec); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "invalid deployment metadata: " + err.Error()})
		return
	}
	if len(deploymentDB.GetByName(ld.GetSpecName())) > 0 {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "deployment " + ld.GetSpecName() + " already exists."})
		return
	}

	ph := photonDB.GetByID(ld.Spec.PhotonID)
	if ph == nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "photon " + ld.Spec.PhotonID + " does not exist."})
		return
	}

	ld.Spec.LeptonDeploymentSystemSpec = leptonaiv1alpha1.LeptonDeploymentSystemSpec{
		PhotonName:         ph.GetSpecName(),
		PhotonImage:        ph.Spec.Image,
		BucketName:         *bucketNameFlag,
		PhotonPrefix:       *photonPrefixFlag,
		ServiceAccountName: *serviceAccountNameFlag,
		RootDomain:         *rootDomainFlag,
		CertificateARN:     *certificateARNFlag,
	}
	if len(*apiTokenFlag) > 0 {
		ld.Spec.APITokens = []string{*apiTokenFlag}
	}
	ld.Namespace = *namespaceFlag
	ld.Name = ld.GetSpecName()

	if err := util.K8sClient.Create(context.Background(), ld); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create deployment CR: " + err.Error()})
		return
	}

	ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateStarting

	c.JSON(http.StatusOK, httpapi.NewLeptonDeployment(ld).Output())
}

func deploymentListHandler(c *gin.Context) {
	lds := deploymentDB.GetAll()
	ret := make([]*httpapi.LeptonDeployment, 0, len(lds))
	for _, ld := range lds {
		ret = append(ret, httpapi.NewLeptonDeployment(ld).Output())
	}
	c.JSON(http.StatusOK, ret)
}

func deploymentPatchHandler(c *gin.Context) {
	did := c.Param("did")
	ld := deploymentDB.GetByID(did)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "deployment " + did + " does not exist."})
		return
	}

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to read request body: " + err.Error()})
		return
	}

	ldi := &leptonaiv1alpha1.LeptonDeploymentUserSpec{}
	if err := json.Unmarshal(body, &ldi); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "failed to get deployment metadata: " + err.Error()})
		return
	}
	if err := validatePatchInput(ldi); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "invalid patch metadata: " + err.Error()})
		return
	}

	ld.Patch(ldi)
	ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateUpdating

	if err := util.K8sClient.Update(context.Background(), ld); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to patch deployment CR " + ld.GetSpecName() + ": " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, httpapi.NewLeptonDeployment(ld).Output())
}

func deploymentGetHandler(c *gin.Context) {
	did := c.Param("did")
	ld := deploymentDB.GetByID(did)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "deployment " + did + " does not exist."})
		return
	}

	c.JSON(http.StatusOK, httpapi.NewLeptonDeployment(ld).Output())
}

func deploymentDeleteHandler(c *gin.Context) {
	did := c.Param("did")
	ld := deploymentDB.GetByID(did)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidParameterValue, "message": "deployment " + did + " does not exist."})
		return
	}
	if err := util.K8sClient.Delete(context.Background(), ld); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to delete deployment " + did + " crd: " + err.Error()})
		return
	}
	c.Status(http.StatusOK)
}

func validateDeploymentInput(ld *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
	if !util.ValidateName(ld.Name) {
		return fmt.Errorf("invalid name %s: %s", ld.Name, util.NameInvalidMessage)
	}
	if ld.ResourceRequirement.CPU <= 0 {
		return fmt.Errorf("cpu must be positive")
	}
	if ld.ResourceRequirement.Memory <= 0 {
		return fmt.Errorf("memory must be positive")
	}
	if ld.ResourceRequirement.MinReplicas <= 0 {
		return fmt.Errorf("min replicas must be positive")
	}
	ph := photonDB.GetByID(ld.PhotonID)
	if ph == nil {
		return fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}
	return nil
}

func validatePatchInput(ld *leptonaiv1alpha1.LeptonDeploymentUserSpec) error {
	valid := false
	if ld.ResourceRequirement.MinReplicas > 0 {
		valid = true
	}
	if ld.PhotonID != "" {
		ph := photonDB.GetByID(ld.PhotonID)
		if ph == nil {
			return fmt.Errorf("photon %s does not exist", ld.PhotonID)
		}
		valid = true
	}
	if !valid {
		return fmt.Errorf("no valid field to patch")
	}
	return nil
}
