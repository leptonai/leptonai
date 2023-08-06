package secret

import (
	"context"

	"github.com/leptonai/lepton/go-pkg/k8s"

	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

const SecretObjectName = "lepton-deployment-secret"

// ListAllSecretSets lists all secret set in a namespace
func ListAllSecretSets(ctx context.Context, ns string) ([]string, error) {
	secrets := &corev1.SecretList{}

	err := k8s.MustLoadDefaultClient().List(ctx, secrets, &client.ListOptions{
		Namespace: ns,
	})
	if err != nil {
		return nil, err
	}

	var ss []string

	for _, secret := range secrets.Items {
		ss = append(ss, secret.Name)
	}

	return ss, nil
}
