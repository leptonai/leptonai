package secret

import (
	"context"

	"github.com/leptonai/lepton/go-pkg/k8s"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
)

type SecretSet struct {
	NamespacedName types.NamespacedName
}

type SecretItem struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

func New(namespace, secretSetName string) *SecretSet {
	return &SecretSet{
		NamespacedName: types.NamespacedName{
			Namespace: namespace,
			Name:      secretSetName,
		},
	}
}

func (s *SecretSet) List() ([]string, error) {
	secret := &corev1.Secret{}
	err := k8s.Client.Get(context.Background(), s.NamespacedName, secret)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return nil, err
		}
		return nil, nil
	}
	ret := make([]string, 0, len(secret.Data))
	for key := range secret.Data {
		ret = append(ret, key)
	}
	return ret, nil
}

func (s *SecretSet) Put(secrets []SecretItem) error {
	secret := &corev1.Secret{}
	err := k8s.Client.Get(context.Background(), s.NamespacedName, secret)
	exist := true
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		secret = &corev1.Secret{
			ObjectMeta: metav1.ObjectMeta{
				Name:      s.NamespacedName.Name,
				Namespace: s.NamespacedName.Namespace,
			},
		}
		exist = false
	}
	// have to initialize the map for both update and create, because StringData
	// is write only and get always returns a nil map
	secret.StringData = make(map[string]string)
	for _, item := range secrets {
		if len(item.Value) > 0 {
			secret.StringData[item.Name] = item.Value
		}
	}
	if exist {
		return k8s.Client.Update(context.Background(), secret)
	} else {
		return k8s.Client.Create(context.Background(), secret)
	}
}

func (s *SecretSet) Delete(keys ...string) error {
	secret := &corev1.Secret{}
	err := k8s.Client.Get(context.Background(), s.NamespacedName, secret)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		return nil
	}
	for _, key := range keys {
		delete(secret.Data, key)
	}
	return k8s.Client.Update(context.Background(), secret)
}

func (s *SecretSet) Destroy() error {
	secret := &corev1.Secret{}
	err := k8s.Client.Get(context.Background(), s.NamespacedName, secret)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		return nil
	}
	return k8s.Client.Delete(context.Background(), secret)
}
