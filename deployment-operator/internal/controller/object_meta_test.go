package controller

import (
	"reflect"
	"testing"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func TestCompareAndPatchLabels(t *testing.T) {
	tests := []struct {
		meta     map[string]string
		patch    map[string]string
		equals   bool
		expected map[string]string
	}{
		{
			meta: map[string]string{
				"foo": "bar",
			},
			patch: map[string]string{
				"foo": "bar",
			},
			equals: true,
			expected: map[string]string{
				"foo": "bar",
			},
		},
		{
			meta: map[string]string{
				"foo": "bar",
			},
			patch: map[string]string{
				"foo": "baz",
			},
			equals: false,
			expected: map[string]string{
				"foo": "baz",
			},
		},
		{
			meta: map[string]string{
				"foo": "bar",
			},
			patch: map[string]string{
				"bar": "baz",
			},
			equals: false,
			expected: map[string]string{
				"foo": "bar",
				"bar": "baz",
			},
		},
	}

	for i, test := range tests {
		meta := &metav1.ObjectMeta{
			Labels: test.meta,
		}
		patch := &metav1.ObjectMeta{
			Labels: test.patch,
		}
		equals := compareAndPatchLabels(meta, patch)
		if equals != test.equals {
			t.Errorf("Test %d: Expected equals to be %v, got %v", i, test.equals, equals)
		}
		if !reflect.DeepEqual(meta.Labels, test.expected) {
			t.Errorf("Test %d: Expected meta to be %v, got %v", i, test.expected, meta.Labels)
		}
	}
}

func TestCompareAndPatchAnnotations(t *testing.T) {
	tests := []struct {
		meta     map[string]string
		patch    map[string]string
		equals   bool
		expected map[string]string
	}{
		{
			meta: map[string]string{
				"foo": "bar",
			},
			patch: map[string]string{
				"foo": "bar",
			},
			equals: true,
			expected: map[string]string{
				"foo": "bar",
			},
		},
		{
			meta: map[string]string{
				"foo": "bar",
			},
			patch: map[string]string{
				"foo": "baz",
			},
			equals: false,
			expected: map[string]string{
				"foo": "baz",
			},
		},
		{
			meta: map[string]string{
				"foo": "bar",
			},
			patch: map[string]string{
				"bar": "baz",
			},
			equals: false,
			expected: map[string]string{
				"foo": "bar",
				"bar": "baz",
			},
		},
	}

	for i, test := range tests {
		meta := &metav1.ObjectMeta{
			Annotations: test.meta,
		}
		patch := &metav1.ObjectMeta{
			Annotations: test.patch,
		}
		equals := compareAndPatchAnnotations(meta, patch)
		if equals != test.equals {
			t.Errorf("Test %d: Expected equals to be %v, got %v", i, test.equals, equals)
		}
		if !reflect.DeepEqual(meta.Annotations, test.expected) {
			t.Errorf("Test %d: Expected meta to be %v, got %v", i, test.expected, meta.Annotations)
		}
	}
}

func TestCompareAndPatchOwnerReferences(t *testing.T) {
	tests := []struct {
		meta     []metav1.OwnerReference
		patch    []metav1.OwnerReference
		equals   bool
		expected []metav1.OwnerReference
	}{
		{
			meta: []metav1.OwnerReference{
				{
					APIVersion: "foo",
					Kind:       "bar",
					Name:       "baz",
				},
			},
			patch: []metav1.OwnerReference{
				{
					APIVersion: "foo",
					Kind:       "bar",
					Name:       "baz",
				},
			},
			equals: true,
			expected: []metav1.OwnerReference{
				{
					APIVersion: "foo",
					Kind:       "bar",
					Name:       "baz",
				},
			},
		},
		{
			meta: []metav1.OwnerReference{
				{
					APIVersion: "foo",
					Kind:       "bar",
					Name:       "baz",
				},
			},
			patch: []metav1.OwnerReference{
				{
					APIVersion: "foo",
					Kind:       "bar",
					Name:       "qux",
				},
			},
			equals: false,
			expected: []metav1.OwnerReference{
				{
					APIVersion: "foo",
					Kind:       "bar",
					Name:       "qux",
				},
			},
		},
	}

	for i, test := range tests {
		meta := &metav1.ObjectMeta{
			OwnerReferences: test.meta,
		}
		patch := &metav1.ObjectMeta{
			OwnerReferences: test.patch,
		}
		equals := compareAndPatchOwnerReferences(meta, patch)
		if equals != test.equals {
			t.Errorf("Test %d: Expected equals to be %v, got %v", i, test.equals, equals)
		}
		if !reflect.DeepEqual(meta.OwnerReferences, test.expected) {
			t.Errorf("Test %d: Expected meta to be %v, got %v", i, test.expected, meta.OwnerReferences)
		}
	}
}
