package k8s

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// GetResourceQuota returns the ResourceQuota object for the given namespace.
func GetResourceQuota(ctx context.Context, namespace, name string) (v1.ResourceQuota, error) {
	quota := v1.ResourceQuota{}
	err := Client.Get(ctx, client.ObjectKey{Namespace: namespace, Name: name}, &quota)
	return quota, err
}
