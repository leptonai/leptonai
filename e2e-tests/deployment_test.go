package e2etests

import (
	"context"
	"fmt"
	"os/exec"
	"testing"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/util"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func TestDeploymentCreate(t *testing.T) {
	name := "deploy-" + randString(5)

	mustCreatePhoton(t, name)
	mustPushPhoton(t, name)

	mustDeployPhoton(t, name)

	mustVerifyDeployment(t, name)
}

func mustDeployPhoton(t *testing.T, name string) {
	id := getPhotonID(name, mustListPhoton(t))

	cmd := exec.Command("lepton", "photon", "run", "-i", id, "-r", *remoteURL)
	out, err := cmd.Output()
	if err != nil {
		fmt.Println(string(out))
		t.Fatal(err)
	}
}

func mustVerifyDeployment(t *testing.T, name string) {
	clientset := util.MustInitK8sClientSet()

	labelSelector := "photon_name=" + name
	listOptions := metav1.ListOptions{
		LabelSelector: labelSelector,
	}

	deployments, err := clientset.AppsV1().Deployments(*namespace).List(context.TODO(), listOptions)
	if err != nil {
		t.Fatal(err)
	}

	if len(deployments.Items) == 0 {
		t.Fatalf("no deployment found with label selector: %s\n", labelSelector)
	}

	d := &deployments.Items[0]

	if *d.Spec.Replicas != 1 {
		t.Error("deployment replicas is not 1")
	}
	// TODO: verify other fields

	timeoutc := time.After(10 * time.Minute)
	ready := false
	for !ready {
		select {
		case <-time.After(5 * time.Second):
			deployments, err := clientset.AppsV1().Deployments(*namespace).List(context.TODO(), listOptions)
			if err != nil {
				t.Fatal(err)
			}

			if deployments.Items[0].Status.ReadyReplicas == deployments.Items[0].Status.Replicas {
				ready = true
			}

		case <-timeoutc:
			t.Fatalf("timeout waiting for deployment '%s' to become ready\n", name)
		}
	}
}
