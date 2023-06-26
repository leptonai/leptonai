package k8s

import (
	"context"
	"log"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// CreatePV creates a PersistentVolume object points to the EFS volume Handle.
func CreatePV(name string, volumeHandle string) error {
	mode := corev1.PersistentVolumeFilesystem
	csiDriver := "efs.csi.aws.com"

	// Create the PersistentVolume object
	pv := &corev1.PersistentVolume{
		ObjectMeta: metav1.ObjectMeta{
			Name: name,
		},
		Spec: corev1.PersistentVolumeSpec{
			Capacity: corev1.ResourceList{
				corev1.ResourceStorage: resource.MustParse("5Gi"),
			},
			VolumeMode: &mode,
			AccessModes: []corev1.PersistentVolumeAccessMode{
				corev1.ReadWriteMany,
			},
			PersistentVolumeReclaimPolicy: corev1.PersistentVolumeReclaimRetain,
			MountOptions:                  []string{"tls"},
			PersistentVolumeSource: corev1.PersistentVolumeSource{
				CSI: &corev1.CSIPersistentVolumeSource{
					Driver:       csiDriver,
					VolumeHandle: volumeHandle,
				},
			},
			StorageClassName: "efs-sc",
		},
	}

	err := Client.Create(context.TODO(), pv)
	if err != nil {
		return err
	}
	log.Printf("Created PersistentVolume %q\n", pv.GetObjectMeta().GetName())

	return nil
}

// DeletePV deletes the PersistentVolume object with the given name.
func DeletePV(name string) error {
	pv := &corev1.PersistentVolume{
		ObjectMeta: metav1.ObjectMeta{
			Name: name,
		},
	}

	err := Client.Delete(context.Background(), pv)
	if err != nil {
		return err
	}
	log.Printf("Deleted PersistentVolume %q\n", pv.GetObjectMeta().GetName())

	return nil
}

// CreatePVC creates a PersistentVolumeClaim object points to the PV with the given name.
func CreatePVC(namespace, name, pvname string, or []metav1.OwnerReference) error {
	storageClass := "efs-sc"
	pvc := &corev1.PersistentVolumeClaim{
		ObjectMeta: metav1.ObjectMeta{
			Name:            name,
			Namespace:       namespace,
			OwnerReferences: or,
		},
		Spec: corev1.PersistentVolumeClaimSpec{
			VolumeName: pvname,
			AccessModes: []corev1.PersistentVolumeAccessMode{
				corev1.ReadWriteMany,
			},
			Resources: corev1.ResourceRequirements{
				Requests: corev1.ResourceList{
					corev1.ResourceStorage: resource.MustParse("5Gi"),
				},
			},
			StorageClassName: &storageClass,
		},
	}

	err := Client.Create(context.Background(), pvc)
	if err != nil {
		return err
	}

	log.Printf("Created PersistentVolumeClaim %q\n", pvc.GetObjectMeta().GetName())
	return nil
}

// DeletePVC deletes the PersistentVolumeClaim object with the given name.
func DeletePVC(namespace, name string) error {
	pvc := &corev1.PersistentVolumeClaim{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
		},
	}

	err := Client.Delete(context.Background(), pvc)
	if err != nil {
		return err
	}
	log.Printf("Deleted PersistentVolumeClaim %q\n", pvc.GetObjectMeta().GetName())

	return nil
}
