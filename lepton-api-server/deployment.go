package main

import (
	"context"
	"log"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	"k8s.io/apimachinery/pkg/watch"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/namedb"
)

var deploymentDB = namedb.NewNameDB[leptonaiv1alpha1.LeptonDeployment]()

func initDeployments() {
	deploymentDB.Clear()
	// Watch for changes in the LeptonDeployment CR
	ch, err := k8s.Client.Watch(context.Background(),
		&leptonaiv1alpha1.LeptonDeploymentList{},
		client.InNamespace(*namespaceFlag))
	if err != nil {
		log.Fatalln(err)
	}
	// We have to finish processing all events in the channel before
	// continuing the startup process
	log.Println("rebuilding api server state for lepton deployments...")
	drainAndProcessExistingEvents(ch.ResultChan(), processLeptonDeploymentEvent)
	log.Println("restored api server state for lepton deployments")
	// Watch for future changes
	go func() {
		log.Println("LeptonDeployment watcher started")
		defer func() {
			log.Println("LeptonDeployment watcher exited, restarting...")
			// TODO when we re-initialize the db, users may temporarily see an
			// in-complete list (though the time is very short)
			go initDeployments()
		}()
		for event := range ch.ResultChan() {
			processLeptonDeploymentEvent(event)
		}
	}()
}

func processLeptonDeploymentEvent(event watch.Event) {
	ld := event.Object.(*leptonaiv1alpha1.LeptonDeployment)
	log.Println("LeptonDeployment CR event:", event.Type, ld.Name)
	switch event.Type {
	case watch.Added:
		deploymentDB.Add(ld)
	case watch.Modified:
		deploymentDB.Add(ld)
	case watch.Deleted:
		deploymentDB.Delete(ld)
	}
}
