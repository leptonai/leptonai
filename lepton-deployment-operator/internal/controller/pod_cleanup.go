package controller

import (
	"context"
	"time"

	goutil "github.com/leptonai/lepton/go-pkg/util"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/fields"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// CleanupBadPodsPeriodically cleans up pods with failed status with expected reasons
// (Evicted, UnexpectedAdmissionError, NodeAffinity)
func (r *LeptonDeploymentReconciler) CleanupBadPodsPeriodically(namespace string) {
	for {
		time.Sleep(5 * time.Minute)

		podList := &corev1.PodList{}
		failedSelector := fields.OneTermEqualSelector("status.phase", "Failed")

		podListOptions := client.ListOptions{
			Namespace:     namespace,
			FieldSelector: failedSelector,
		}

		err := r.Client.List(context.Background(), podList, &podListOptions)
		if err != nil {
			goutil.Logger.Errorw("failed to get pods with failed status",
				"operation", "cleanupBadPods",
				"namespace", namespace,
				"error", err,
			)
			continue
		}

		for _, pod := range podList.Items {
			if pod.Status.Phase != corev1.PodFailed {
				goutil.Logger.Errorw("pod is not in failed state",
					"operation", "cleanupBadPods",
					"namespace", namespace,
					"pod", pod.Name,
					"phase", pod.Status.Phase,
				)
				continue
			}
			if pod.Status.Reason != "Evicted" && pod.Status.Reason != "UnexpectedAdmissionError" &&
				pod.Status.Reason != "NodeAffinity" {
				goutil.Logger.Warnw("failed pod is not in expected state. skipping and waitting for the default GC to cleanup",
					"operation", "cleanupBadPods",
					"namespace", namespace,
					"pod", pod.Name,
					"reason", pod.Status.Reason,
				)
				continue
			}
			err = r.Client.Delete(context.Background(), &pod)
			if err != nil {
				goutil.Logger.Errorw("failed to delete pod",
					"operation", "cleanupBadPods",
					"namespace", namespace,
					"pod", pod.Name,
					"error", err,
				)
			} else {
				goutil.Logger.Infow("pod deleted",
					"operation", "cleanupBadPods",
					"namespace", namespace,
					"pod", pod.Name,
				)
			}
		}
	}
}
