package k8s

import (
	"context"
	"time"

	eventv1 "k8s.io/api/events/v1"
	"k8s.io/apimachinery/pkg/fields"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// ListPodEvents returns a list of events for a pod
func ListPodEvents(ctx context.Context, namespace, name string) (*eventv1.EventList, error) {
	return ListEvents(ctx, namespace, name, "Pod")
}

// ListDeploymentEvents returns a list of events for a deployment
func ListDeploymentEvents(ctx context.Context, namespace, name string) (*eventv1.EventList, error) {
	return ListEvents(ctx, namespace, name, "Deployment")
}

// ListEvents returns a list of events for a resource
func ListEvents(ctx context.Context, namespace, name, kind string) (*eventv1.EventList, error) {
	selector := fields.SelectorFromSet(fields.Set{
		"regarding.kind": kind,
		"regarding.name": name,
	})

	// A relative high timeout since k8s list can be slow
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	events := &eventv1.EventList{}
	err := MustLoadDefaultClient().List(ctx, events, &client.ListOptions{
		Namespace:     namespace,
		FieldSelector: selector,
	})
	if err != nil {
		return nil, err
	}

	return events, nil
}
