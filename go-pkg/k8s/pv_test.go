package k8s

import (
	"context"
	"testing"

	"github.com/leptonai/lepton/go-pkg/util"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

func TestPVandPVC(t *testing.T) {
	name := "test-pv-" + util.RandString(5)
	handle := "fs-12345678"
	err := CreatePV(name, handle, nil)
	if err != nil {
		t.Fatal("failed to create PV:", err)
	}
	defer func() {
		err = DeletePV(name)
		if err != nil {
			t.Fatal("failed to delete PV:", err)
		}
	}()

	// Make this a sub test
	pv := &corev1.PersistentVolume{}
	err = Client.Get(context.Background(), types.NamespacedName{Name: name}, pv, &client.GetOptions{})
	if err != nil {
		t.Fatal("failed to get PV:", err)
	}
	if pv.Name != name {
		t.Error("expected name:", name, "got:", pv.Name)
	}
	if pv.Spec.CSI.VolumeHandle != handle {
		t.Error("expected handle:", handle, "got:", pv.Spec.CSI.VolumeHandle)
	}

	// Make this a sub test
	cname := "test-pvc-" + util.RandString(5)
	namespace := "default"

	err = CreatePVC(namespace, cname, name, nil)
	if err != nil {
		t.Fatal("failed to create PVC:", err)
	}
	defer func() {
		err = DeletePVC(namespace, cname)
		if err != nil {
			t.Fatal("failed to delete PVC:", err)
		}
	}()

	pvc := &corev1.PersistentVolumeClaim{}
	err = Client.Get(context.Background(), types.NamespacedName{Namespace: namespace, Name: cname}, pvc, &client.GetOptions{})
	if err != nil {
		t.Fatal("failed to get PVC:", err)
	}
	if pvc.Name != cname {
		t.Error("expected name:", cname, "got:", pvc.Name)
	}
	if pvc.Spec.VolumeName != name {
		t.Error("expected name:", name, "got:", pvc.Spec.VolumeName)
	}
}
