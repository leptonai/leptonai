package httpapi

import (
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

type LeptonDeployment struct {
	LeptonDeploymentMetadata                  `json:",inline"`
	leptonaiv1alpha1.LeptonDeploymentUserSpec `json:",inline"`
	Status                                    leptonaiv1alpha1.LeptonDeploymentStatus `json:"status,omitempty"`
}

type LeptonDeploymentMetadata struct {
	ID        string `json:"id"`
	CreatedAt int64  `json:"created_at"`
}

func NewLeptonDeploymentMetadata(ld *leptonaiv1alpha1.LeptonDeployment) *LeptonDeploymentMetadata {
	return &LeptonDeploymentMetadata{
		ID:        ld.GetID(),
		CreatedAt: ld.CreationTimestamp.UnixMilli(),
	}
}

func NewLeptonDeployment(ld *leptonaiv1alpha1.LeptonDeployment) *LeptonDeployment {
	return &LeptonDeployment{
		LeptonDeploymentUserSpec: ld.Spec.LeptonDeploymentUserSpec,
		LeptonDeploymentMetadata: *NewLeptonDeploymentMetadata(ld),
		Status:                   ld.Status,
	}
}

func (ld *LeptonDeployment) Output() *LeptonDeployment {
	return &LeptonDeployment{
		LeptonDeploymentUserSpec: ld.LeptonDeploymentUserSpec,
		LeptonDeploymentMetadata: ld.LeptonDeploymentMetadata,
		Status:                   ld.Status,
	}
}
