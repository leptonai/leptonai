package datastore

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/go-pkg/k8s"

	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// TODO: add tests (have to figure out how to mock k8s first)
type CRStore[T client.Object] struct {
	namespace string
	example   T
}

func NewCRStore[T client.Object](namespace string, example T) *CRStore[T] {
	return &CRStore[T]{
		namespace: namespace,
		example:   example,
	}
}

func (s *CRStore[T]) Create(name string, t T) error {
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Create(context.Background(), t)
}

func (s *CRStore[T]) Get(name string) (T, error) {
	t := s.example.DeepCopyObject().(T)
	err := k8s.Client.Get(context.Background(), client.ObjectKey{
		Namespace: s.namespace,
		Name:      name,
	}, t)
	return t, err
}

func (s *CRStore[T]) List() ([]T, error) {
	gvks, _, err := k8s.Client.Scheme().ObjectKinds(s.example)
	if err != nil {
		return nil, err
	}
	if len(gvks) != 1 {
		return nil, fmt.Errorf("expected exactly one GVK, got %d", len(gvks))
	}
	gvk := gvks[0]
	tList := &unstructured.UnstructuredList{}
	tList.SetGroupVersionKind(gvk)
	if err := k8s.Client.List(context.Background(), tList, client.InNamespace(s.namespace)); err != nil {
		return nil, err
	}
	ts := make([]T, 0, len(tList.Items))
	for _, item := range tList.Items {
		t := s.example.DeepCopyObject().(T)
		err := runtime.DefaultUnstructuredConverter.FromUnstructured(item.Object, &t)
		if err != nil {
			return nil, err
		}
		ts = append(ts, t)
	}
	return ts, nil
}

func (s *CRStore[T]) Update(name string, t T) error {
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Update(context.Background(), t)
}

func (s *CRStore[T]) Delete(name string) error {
	t := s.example.DeepCopyObject().(T)
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Delete(context.Background(), t)
}
