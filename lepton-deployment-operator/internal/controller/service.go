package controller

import (
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

type Service struct {
	leptonDeployment *leptonaiv1alpha1.LeptonDeployment
}

func newService(ld *leptonaiv1alpha1.LeptonDeployment) *Service {
	return &Service{
		leptonDeployment: ld,
	}
}

func (k *Service) createService(or []metav1.OwnerReference) *corev1.Service {
	ld := k.leptonDeployment
	service := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:            service.ServiceName(ld.GetSpecName()),
			Namespace:       ld.Namespace,
			OwnerReferences: or,
		},
		Spec: corev1.ServiceSpec{
			Selector: map[string]string{
				labelKeyLeptonDeploymentID: ld.GetSpecID(),
			},
			Ports: []corev1.ServicePort{
				{
					Port:     service.Port,
					Protocol: corev1.ProtocolTCP,
				},
			},
		},
	}
	return service
}