package e2etests

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os/exec"
	"testing"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func TestDeploymentCreateAndList(t *testing.T) {
	before := mustListDeployment(t)

	name := "deploy-" + randString(5)
	mustCreatePhoton(t, name)
	mustPushPhoton(t, name)
	mustDeployPhoton(t, name)

	mustVerifyDeployment(t, name)

	after := mustListDeployment(t)

	if len(after) != len(before)+1 {
		t.Fatal("deployment list length is not correct")
	}
}

func TestDeploymentRemove(t *testing.T) {
	before := mustListDeployment(t)

	name := "deploy-" + randString(5)
	mustCreatePhoton(t, name)
	mustPushPhoton(t, name)
	mustDeployPhoton(t, name)
	mustVerifyDeployment(t, name)

	pid := getPhotonID(name, mustListPhoton(t))
	did := mustGetDeploymentIDbyPhotonID(t, pid)
	mustRemoveDeploymentByID(t, did)

	after := mustListDeployment(t)

	if len(after) != len(before) {
		t.Fatal("failed to remove deployment")
	}
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

func mustListDeployment(t *testing.T) []httpapi.LeptonDeployment {
	c := http.Client{}
	r, err := c.Get(*remoteURL + "/deployments")
	if err != nil {
		t.Fatal(err)
	}
	defer r.Body.Close()

	if r.StatusCode != http.StatusOK {
		t.Fatalf("Request failed with status code: %d", r.StatusCode)
	}

	var ds []httpapi.LeptonDeployment
	err = json.NewDecoder(r.Body).Decode(&ds)
	if err != nil {
		t.Fatal(err)
	}

	return ds
}

func mustGetDeploymentIDbyPhotonID(t *testing.T, pid string) string {
	ds := mustListDeployment(t)

	for _, d := range ds {
		if d.PhotonID == pid {
			return d.ID
		}
	}

	t.Fatal("deployment not found")

	return ""
}

func mustRemoveDeploymentByID(t *testing.T, id string) {
	c := http.Client{}

	req, err := http.NewRequest(http.MethodDelete, *remoteURL+"/deployments/"+id, nil)
	if err != nil {
		t.Fatal(err)
	}

	resp, err := c.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("Delete failed with status code: %d", resp.StatusCode)
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
