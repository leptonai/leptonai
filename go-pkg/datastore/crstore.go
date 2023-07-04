package datastore

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/go-pkg/k8s"

	apierrors "k8s.io/apimachinery/pkg/api/errors"
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

func (s *CRStore[T]) Create(ctx context.Context, name string, t T) error {
	// when CRD "kindMatchErr.GroupKind" is not installed, its controller will be no-op
	// returning "*meta.NoKindMatchError" error type, but we don't care about this case now
	// ref. https://github.com/openkruise/kruise/blob/6ca91fe04e521dafbd7d8170d03c3af4072ac645/pkg/controller/controllers.go#L75
	if _, err := s.Get(ctx, name); !apierrors.IsNotFound(err) {
		return fmt.Errorf("cluster %q already exists", name)
	}

	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Create(ctx, t)
}

func (s *CRStore[T]) UpdateStatus(ctx context.Context, name string, t T) error {
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Status().Update(ctx, t)
}

func (s *CRStore[T]) Get(ctx context.Context, name string) (T, error) {
	t := s.example.DeepCopyObject().(T)
	err := k8s.Client.Get(ctx, client.ObjectKey{
		Namespace: s.namespace,
		Name:      name,
	}, t)
	return t, err
}

func (s *CRStore[T]) List(ctx context.Context) ([]T, error) {
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
	if err := k8s.Client.List(ctx, tList, client.InNamespace(s.namespace)); err != nil {
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

func (s *CRStore[T]) Update(ctx context.Context, name string, t T) error {
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Update(ctx, t)
}

func (s *CRStore[T]) Delete(ctx context.Context, name string) error {
	t := s.example.DeepCopyObject().(T)
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.Client.Delete(ctx, t)
}
