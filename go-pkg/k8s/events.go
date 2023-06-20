package k8s

import (
	"context"

	eventv1 "k8s.io/api/events/v1"
	"k8s.io/apimachinery/pkg/fields"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

func ListDeploymentEvents(namespace, name string) (*eventv1.EventList, error) {
	selector := fields.SelectorFromSet(fields.Set{
		"regarding.kind": "Deployment",
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
