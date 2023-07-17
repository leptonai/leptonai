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
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/runtime/serializer/json"
	"k8s.io/client-go/kubernetes/scheme"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// TODO: add tests (have to figure out how to mock k8s first)
type CRStore[T client.Object] struct {
	namespace string
	example   T

	backupBucket *blob.Bucket
}

func NewCRStore[T client.Object](namespace string, example T, backupBucket *blob.Bucket) *CRStore[T] {
	return &CRStore[T]{
		namespace:    namespace,
		example:      example,
		backupBucket: backupBucket,
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
	gvk, err := s.getGVK()
	if err != nil {
		return nil, err
	}

	tList := &unstructured.UnstructuredList{}
	tList.SetGroupVersionKind(*gvk)
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
	gvk, err := s.getGVK()
	if err != nil {
		return err
	}
	kind := gvk.Kind
	var lastErr error
	for _, t := range ts {
		err := s.Delete(ctx, t.GetName())
		if err != nil {
			goutil.Logger.Errorw("failed to delete CR",
				"operation", "BackupAndDeleteAll",
				"kind", kind,
				"name", t.GetName(),
				"err", err,
			)
			lastErr = err
		} else {
			goutil.Logger.Infow("deleted CR",
				"operation", "BackupAndDeleteAll",
				"kind", kind,
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

	gvk, err := s.getGVK()
	if err != nil {
		return err
	}
	kind := gvk.Kind

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

	ts, err := s.List(ctx)
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
				"kind", kind,
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

	uploadFilename := fmt.Sprintf("backup-%s-%s.tar.gz", kind, time.Now().Format("2006-01-02T15:04:05"))

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
		"kind", kind,
		"filename", uploadFilename,
		"size", n)

	return nil
}

func (s *CRStore[T]) getGVK() (*schema.GroupVersionKind, error) {
	gvks, _, err := k8s.Client.Scheme().ObjectKinds(s.example)
	if err != nil {
		return nil, err
	}
	if len(gvks) != 1 {
		return nil, fmt.Errorf("expected exactly one GVK, got %d", len(gvks))
	}
	gvk := gvks[0]
	return &gvk, nil
}
