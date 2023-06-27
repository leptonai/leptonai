package controller

import (
	"fmt"
	"sync"
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func getOwnerRefFromService(s *corev1.Service) *metav1.OwnerReference {
	return &metav1.OwnerReference{
		APIVersion: "v1",
		Kind:       "Service",
		Name:       s.Name,
		UID:        s.UID,
	}
}

func getOwnerRefFromLeptonDeployment(ld *leptonaiv1alpha1.LeptonDeployment) *metav1.OwnerReference {
	blockOwnerDeletion := true
	isController := true
	return &metav1.OwnerReference{
		APIVersion:         ld.APIVersion,
		Kind:               ld.Kind,
		Name:               ld.Name,
		UID:                ld.UID,
		BlockOwnerDeletion: &blockOwnerDeletion,
		Controller:         &isController,
	}
}

func drainChan(ch chan struct{}) {
	for {
		select {
		case <-ch:
		default:
			return
		}
	}
}

func backoffAndRetry(wg *sync.WaitGroup, ch chan struct{}) {
	defer wg.Done()
	// TODO: avoid hard coding
	// TODO: use exponential backoff
	time.Sleep(10 * time.Second)
	ch <- struct{}{}
}

func getPVName(namespace, name string, id int) string {
	return fmt.Sprintf("pv-%s-%s-%d", namespace, name, id)
}

func getPVCName(namespace, name string, id int) string {
	return fmt.Sprintf("pvc-%s-%s-%d", namespace, name, id)
}
