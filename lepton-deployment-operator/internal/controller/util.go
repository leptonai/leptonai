package controller

import (
	"sync"
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func getOwnerRefFromLeptonDeployment(ld *leptonaiv1alpha1.LeptonDeployment) *metav1.OwnerReference {
	return &metav1.OwnerReference{
		APIVersion: ld.APIVersion,
		Kind:       ld.Kind,
		Name:       ld.Name,
		UID:        ld.UID,
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

func sleepAndPoke(wg *sync.WaitGroup, ch chan struct{}) {
	defer wg.Done()
	// TODO: avoid hard coding
	// TODO: use exponential backoff
	time.Sleep(10 * time.Second)
	ch <- struct{}{}
}
