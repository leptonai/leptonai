package httpapi

import (
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

type Photon struct {
	PhotonMetadata                  `json:",inline"`
	leptonaiv1alpha1.PhotonUserSpec `json:",inline"`
}

type PhotonMetadata struct {
	ID        string `json:"id"`
	CreatedAt int64  `json:"created_at"`
}

func NewPhotonMetadata(p *leptonaiv1alpha1.Photon) *PhotonMetadata {
	return &PhotonMetadata{
		ID:        p.GetSpecID(),
		CreatedAt: p.CreationTimestamp.UnixMilli(),
	}
}

func NewPhoton(p *leptonaiv1alpha1.Photon) *Photon {
	return &Photon{
		PhotonUserSpec: p.Spec.PhotonUserSpec,
		PhotonMetadata: *NewPhotonMetadata(p),
	}
}

func (p *Photon) Output() *Photon {
	return &Photon{
		PhotonUserSpec: p.PhotonUserSpec,
		PhotonMetadata: p.PhotonMetadata,
	}
}
