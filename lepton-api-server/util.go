package main

import (
	"time"

	"k8s.io/apimachinery/pkg/watch"
)

func drainAndProcessExistingEvents(ch <-chan watch.Event, process func(event watch.Event)) {
	for {
		select {
		case event := <-ch:
			process(event)
		// TODO: waiting for 1 second is hacky
		case <-time.After(time.Second):
			return
		}
	}
}
