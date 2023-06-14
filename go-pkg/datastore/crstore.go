package datastore

import (
	"context"

	"github.com/leptonai/lepton/go-pkg/k8s"

	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// TODO: add tests (have to figure out how to mock k8s first)
type CRStore[T client.Object] struct {
	namespace string
}

func NewCRStore[T client.Object](namespace string) *CRStore[T] {
	return &CRStore[T]{
		namespace: namespace,
	}
}

func (s *CRStore[T]) Create(name string, t T) error {
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Create(context.Background(), t)
}

func (s *CRStore[T]) Get(name string) (T, error) {
	var t T
	err := k8s.Client.Get(context.Background(), client.ObjectKey{
		Namespace: s.namespace,
		Name:      name,
	}, t)
	return t, err
}

func (s *CRStore[T]) List() ([]T, error) {
	var t T
	gvk := schema.GroupVersionKind{
		Group:   t.GetObjectKind().GroupVersionKind().Group,
		Version: t.GetObjectKind().GroupVersionKind().Version,
		Kind:    t.GetObjectKind().GroupVersionKind().Kind,
	}
	tList := &unstructured.UnstructuredList{}
	tList.SetGroupVersionKind(gvk)
	err := k8s.Client.List(context.Background(), tList)
	if err != nil {
		return nil, err
	}
	var ts []T
	for _, item := range tList.Items {
		err := runtime.DefaultUnstructuredConverter.FromUnstructured(item.Object, &t)
		if err != nil {
			return nil, err
		}
		ts = append(ts, t.DeepCopyObject().(T))
	}
	return ts, nil
}

func (s *CRStore[T]) Update(name string, t T) error {
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Update(context.Background(), t)
}

func (s *CRStore[T]) Delete(name string) error {
	var t T
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Delete(context.Background(), t)
}
