package httpapi

import (
	"context"
	"log"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	"k8s.io/apimachinery/pkg/watch"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/leptonai/lepton/go-pkg/k8s"
)

func (h *DeploymentHandler) init() {
	h.deploymentDB.Clear()
	// Watch for changes in the LeptonDeployment CR
	ch, err := k8s.Client.Watch(context.Background(),
		&leptonaiv1alpha1.LeptonDeploymentList{},
		client.InNamespace(h.namespace))
	if err != nil {
		log.Fatalln(err)
	}
	// We have to finish processing all events in the channel before
	// continuing the startup process
	log.Println("rebuilding api server state for lepton deployments...")
	drainAndProcessExistingEvents(ch.ResultChan(), h.processEvent)
	log.Println("restored api server state for lepton deployments")
	// Watch for future changes
	go func() {
		log.Println("LeptonDeployment watcher started")
		defer func() {
			log.Println("LeptonDeployment watcher exited, restarting...")
			// TODO when we re-initialize the db, users may temporarily see an
			// in-complete list (though the time is very short)
			go h.init()
		}()
		for event := range ch.ResultChan() {
			h.processEvent(event)
		}
	}()
}

func (h *DeploymentHandler) processEvent(event watch.Event) {
	ld := event.Object.(*leptonaiv1alpha1.LeptonDeployment)
	log.Println("LeptonDeployment CR event:", event.Type, ld.Name)
	switch event.Type {
	case watch.Added:
		h.deploymentDB.Add(ld)
	case watch.Modified:
		h.deploymentDB.Add(ld)
	case watch.Deleted:
		h.deploymentDB.Delete(ld)
	}
}
