package datastore

import (
	"context"
	"fmt"
	"os"
	"path"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	archiver "github.com/mholt/archiver/v3"
	"gocloud.dev/blob"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/runtime/serializer/json"
	"k8s.io/client-go/kubernetes/scheme"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

const (
	// DefaultDatastoreOperationTimeout is the default timeout for datastore operations
	DefaultDatastoreOperationTimeout = 30 * time.Second
)

// TODO: add tests (have to figure out how to mock k8s first)
type CRStore[T client.Object] struct {
	namespace string
	kind      string
	example   T

	backupBucket *blob.Bucket
}

func NewCRStore[T client.Object](namespace string, example T, backupBucket *blob.Bucket) *CRStore[T] {
	cs := &CRStore[T]{
		namespace:    namespace,
		example:      example,
		backupBucket: backupBucket,
	}

	gvk, err := cs.getGVK()
	if err != nil {
		panic(err)
	}
	cs.kind = gvk.Kind

	return cs
}

func (s *CRStore[T]) Create(ctx context.Context, name string, t T) error {
	st := time.Now()
	defer maybeLogTookTooLong("create", s.kind, s.namespace, st)

	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.MustLoadDefaultClient().Create(ctx, t)
}

func (s *CRStore[T]) UpdateStatus(ctx context.Context, name string, t T) error {
	st := time.Now()
	defer maybeLogTookTooLong("updateStatus", s.kind, s.namespace, st)

	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.MustLoadDefaultClient().Status().Update(ctx, t)
}

func (s *CRStore[T]) Get(ctx context.Context, name string) (T, error) {
	st := time.Now()
	defer maybeLogTookTooLong("get", s.kind, s.namespace, st)

	t := s.example.DeepCopyObject().(T)
	err := k8s.MustLoadDefaultClient().Get(ctx, client.ObjectKey{
		Namespace: s.namespace,
		Name:      name,
	}, t)
	return t, err
}

func (s *CRStore[T]) List(ctx context.Context) ([]T, error) {
	st := time.Now()
	defer maybeLogTookTooLong("list", s.kind, s.namespace, st)

	gvk, err := s.getGVK()
	if err != nil {
		return nil, err
	}

	tList := &unstructured.UnstructuredList{}
	tList.SetGroupVersionKind(*gvk)
	if err := k8s.MustLoadDefaultClient().List(ctx, tList, client.InNamespace(s.namespace)); err != nil {
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
	st := time.Now()
	defer maybeLogTookTooLong("update", s.kind, s.namespace, st)

	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.MustLoadDefaultClient().Update(ctx, t)
}

func (s *CRStore[T]) Delete(ctx context.Context, name string) error {
	st := time.Now()
	defer maybeLogTookTooLong("delete", s.kind, s.namespace, st)

	t := s.example.DeepCopyObject().(T)
	t.SetNamespace(s.namespace)
	t.SetName(name)
	return k8s.MustLoadDefaultClient().Delete(ctx, t)
}

func (s *CRStore[T]) BackupAndDeleteAll(ctx context.Context) error {
	ts, err := s.List(ctx)
	if err != nil {
		return err
	}
	if len(ts) == 0 {
		return nil
	}
	if err := s.Backup(ctx); err != nil {
		return err
	}

	var lastErr error
	for _, t := range ts {
		err := s.Delete(ctx, t.GetName())
		if err != nil {
			goutil.Logger.Errorw("failed to delete CR",
				"operation", "BackupAndDeleteAll",
				"kind", s.kind,
				"name", t.GetName(),
				"err", err,
			)
			lastErr = err
		} else {
			goutil.Logger.Infow("deleted CR",
				"operation", "BackupAndDeleteAll",
				"kind", s.kind,
				"name", t.GetName(),
			)
		}
	}
	return lastErr
}

// Backup creates a tarball of all CRs in the store and uploads it to the backup bucket.
func (s *CRStore[T]) Backup(ctx context.Context) error {
	if s.backupBucket == nil {
		return fmt.Errorf("backupBucket is not set")
	}

	ts, err := s.List(ctx)
	if err != nil {
		return err
	}
	if len(ts) == 0 {
		goutil.Logger.Infow("no CRs found, skipping backup",
			"operation", "backup",
			"kind", s.kind,
		)
		return nil
	}

	tmpDir, err := os.MkdirTemp(os.TempDir(), "crstore")
	if err != nil {
		return err
	}
	defer os.RemoveAll(tmpDir)

	crdDir := path.Join(tmpDir, "crds")
	err = os.Mkdir(crdDir, 0755)
	if err != nil {
		return err
	}

	js := json.NewSerializerWithOptions(json.DefaultMetaFactory, scheme.Scheme,
		scheme.Scheme, json.SerializerOptions{Yaml: true, Pretty: false, Strict: false})

	for _, t := range ts {
		f, err := os.Create(path.Join(crdDir, t.GetName()))
		if err != nil {
			return err
		}

		err = js.Encode(t, f)
		if err != nil {
			return err
		}
		err = f.Close()
		if err != nil {
			goutil.Logger.Errorw("failed to close file",
				"operation", "backup",
				"kind", s.kind,
				"filename", f.Name(),
				"err", err,
			)
		}
	}

	destFile := path.Join(tmpDir, "backup.tar.gz")
	err = archiver.NewTarGz().Archive([]string{crdDir}, destFile)
	if err != nil {
		return err
	}

	uploadFilename := fmt.Sprintf("backup-%s-%s.tar.gz", s.kind, time.Now().Format("2006-01-02T15:04:05"))

	bw, err := s.backupBucket.NewWriter(ctx, uploadFilename, nil)
	if err != nil {
		return err
	}
	defer bw.Close()

	r, err := os.Open(destFile)
	if err != nil {
		return err
	}
	defer r.Close()

	n, err := bw.ReadFrom(r)
	if err != nil {
		return err
	}

	goutil.Logger.Infow("uploaded backup",
		"operation", "backup",
		"kind", s.kind,
		"filename", uploadFilename,
		"size", n)

	return nil
}

func (s *CRStore[T]) getGVK() (*schema.GroupVersionKind, error) {
	gvks, _, err := k8s.MustLoadDefaultClient().Scheme().ObjectKinds(s.example)
	if err != nil {
		return nil, err
	}
	if len(gvks) != 1 {
		return nil, fmt.Errorf("expected exactly one GVK, got %d", len(gvks))
	}
	gvk := gvks[0]
	return &gvk, nil
}
