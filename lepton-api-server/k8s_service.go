package main

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var serviceNamespace = "default"

const servicePort = 8080

func serviceName(ld *httpapi.LeptonDeployment) string {
	return ld.Name + "-service"
}

func createService(ld *httpapi.LeptonDeployment, ph *httpapi.Photon, or metav1.OwnerReference) error {
	clientset := mustInitK8sClientSet()

	service := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:            serviceName(ld),
			OwnerReferences: []metav1.OwnerReference{or},
		},
		Spec: corev1.ServiceSpec{
			Selector: map[string]string{
				"photon": util.JoinByDash(ph.Name, ph.ID),
			},
			Ports: []corev1.ServicePort{
				{
					Port:     servicePort,
					Protocol: corev1.ProtocolTCP,
				},
			},
		},
	}

	result, err := clientset.CoreV1().Services(serviceNamespace).Create(
		context.Background(),
		service,
		metav1.CreateOptions{},
	)
	if err != nil {
		return err
	}

	fmt.Printf("Created service %q.\n", result.GetName())

	return nil
}
