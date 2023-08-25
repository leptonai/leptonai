package controller

import (
	"reflect"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func compareAndPatchLabels(meta, patch *metav1.ObjectMeta) bool {
	equals := true
	for k, v := range patch.Labels {
		if meta.Labels == nil {
			meta.Labels = make(map[string]string)
		}
		if meta.Labels[k] != v {
			meta.Labels[k] = v
			equals = false
		}
	}
	return equals
}

func compareAndPatchAnnotations(meta, patch *metav1.ObjectMeta) bool {
	equals := true
	for k, v := range patch.Annotations {
		if meta.Annotations == nil {
			meta.Annotations = make(map[string]string)
		}
		if meta.Annotations[k] != v {
			meta.Annotations[k] = v
			equals = false
		}
	}
	return equals
}

func compareAndPatchOwnerReferences(meta, patch *metav1.ObjectMeta) bool {
	equals := true
	if !reflect.DeepEqual(meta.OwnerReferences, patch.OwnerReferences) {
		meta.OwnerReferences = patch.OwnerReferences
		equals = false
	}
	return equals
}
