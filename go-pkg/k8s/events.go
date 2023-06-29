package k8s

import (
	"context"

	eventv1 "k8s.io/api/events/v1"
	"k8s.io/apimachinery/pkg/fields"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

func ListPodEvents(namespace, name string) (*eventv1.EventList, error) {
	return ListEvents(namespace, name, "Pod")
}

func ListDeploymentEvents(namespace, name string) (*eventv1.EventList, error) {
	return ListEvents(namespace, name, "Deployment")
}

func ListEvents(namespace, name, kind string) (*eventv1.EventList, error) {
	selector := fields.SelectorFromSet(fields.Set{
		"regarding.kind": kind,
		"regarding.name": name,
	})

	events := &eventv1.EventList{}
	err := Client.List(context.TODO(), events, &client.ListOptions{
		Namespace:     namespace,
		FieldSelector: selector,
	})
	if err != nil {
		return nil, err
	}

	return events, nil
}
