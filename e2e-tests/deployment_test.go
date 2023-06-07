package e2etests

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os/exec"
	"strings"
	"testing"
	"time"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"
	"sigs.k8s.io/controller-runtime/pkg/client"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	networkingv1 "k8s.io/api/networking/v1"
)

const mainContainerName = "main-container"

func TestDeploymentCreateAndList(t *testing.T) {
	before := mustListDeployment(t)

	phName := "deploy-" + randString(5)
	t.Logf("testing photon %q", phName)

	mustCreatePhoton(t, phName)
	mustPushPhoton(t, phName)
	mustDeployPhoton(t, phName)
	mustVerifyDeployment(t, "deploy-", phName)
	mustVerifyIngress(t, "deploy-")

	after := mustListDeployment(t)
	if len(after) != len(before)+1 {
		t.Fatalf("expected %d+1 deployments but got %d", len(before), len(after))
	}
}

func TestDeploymentRemove(t *testing.T) {
	before := mustListDeployment(t)

	phName := "deploy-" + randString(5)
	t.Logf("testing photon %q", phName)

	mustCreatePhoton(t, phName)
	mustPushPhoton(t, phName)
	mustDeployPhoton(t, phName)
	mustVerifyDeployment(t, "deploy-", phName)
	mustVerifyIngress(t, "deploy-")

	pid := getPhotonID(phName, mustListPhoton(t))
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

	// no specific output for "photon run" command runs
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

func mustVerifyDeployment(t *testing.T, pfx string, phName string) {
	deployments := &appsv1.DeploymentList{}
	err := util.K8sClient.List(context.Background(), deployments, client.InNamespace(*namespace), client.MatchingLabels{"photon_name": phName})
	if err != nil {
		t.Fatal(err)
	}
	if len(deployments.Items) != 1 {
		t.Fatalf("expected only 1 deployment with label photon_name=%q, got %d", phName, len(deployments.Items))
	}

	d := &deployments.Items[0]
	if *d.Spec.Replicas != 1 {
		t.Error("deployment replicas is not 1")
	}

	timeoutc := time.After(10 * time.Minute)
ready:
	for {
		select {
		case <-time.After(5 * time.Second):
			err := util.K8sClient.List(context.Background(), deployments, client.InNamespace(*namespace), client.MatchingLabels{"photon_name": phName})
			if err != nil {
				t.Fatal(err)
			}

			if deployments.Items[0].Status.ReadyReplicas == deployments.Items[0].Status.Replicas {
				break ready
			}

		case <-timeoutc:
			t.Fatalf("timeout waiting for deployment '%s' to become ready\n", phName)
		}
	}

	// get detailed information on a deployment
	// verify other fields
	// make sure main-container has the expected lepton commands
	found := false
	for _, c := range d.Spec.Template.Spec.Containers {
		if c.Name != mainContainerName {
			continue
		}
		for _, arg := range c.Args {
			if strings.Contains(arg, phName) && strings.Contains(arg, phPrepareStr) && strings.Contains(arg, phRunStr) {
				found = true
				break
			}
		}
	}
	if !found {
		mm, _ := json.MarshalIndent(d, "", "\t")
		t.Fatalf("%q does not have 'photon run' command container:\n%s\n", mainContainerName, string(mm))
	}

	timeoutc = time.After(10 * time.Minute)
done:
	for {
		select {
		case <-time.After(5 * time.Second):
			t.Logf("listing pods for the test namespace %q", *namespace)
			pods := &corev1.PodList{}
			err := util.K8sClient.List(context.Background(), pods, client.InNamespace(*namespace))
			if err != nil {
				t.Fatal(err)
			}
			if len(pods.Items) == 0 {
				continue
			}

			// ensure the environment variable and other requirements are pushed down to pods
			runningLeptonPhoton := false
			setAWSEnv := false
			for _, p := range pods.Items {
				if !strings.HasPrefix(p.Name, pfx) {
					continue
				}
				if p.Status.Phase != corev1.PodRunning {
					continue
				}

				for _, c := range p.Spec.Containers {
					if c.Name != mainContainerName {
						continue
					}
					for _, arg := range c.Args {
						if strings.Contains(arg, phPrepareStr) {
							runningLeptonPhoton = true
							break
						}
					}
					for _, env := range c.Env {
						if env.Name == "AWS_WEB_IDENTITY_TOKEN_FILE" {
							setAWSEnv = true
							break
						}
					}
				}
			}
			if runningLeptonPhoton && setAWSEnv {
				break done
			}

		case <-timeoutc:
			t.Fatalf("timeout waiting for deployment '%s' to become ready\n", phName)
		}
	}
}

const phPrepareStr = "lepton photon prepare"
const phRunStr = "lepton photon run"

// ensure ingress is set up correctly
func mustVerifyIngress(t *testing.T, pfx string) {
	timeoutc := time.After(10 * time.Minute)
ready:
	for {
		select {
		case <-time.After(5 * time.Second):
			// ensure ingress is set up correctly
			ings := &networkingv1.IngressList{}
			err := util.K8sClient.List(context.Background(), ings, client.InNamespace(*namespace))
			if err != nil {
				t.Fatal(err)
			}
			found := false
			for _, item := range ings.Items {
				if !strings.HasPrefix(item.GetName(), pfx) {
					continue
				}
				if len(item.Status.LoadBalancer.Ingress) == 0 {
					continue
				}

				// TODO: ensure token checking is set up correctly by access the API directly
				hostName := item.Status.LoadBalancer.Ingress[0].Hostname
				t.Logf("hostname %q found for ingress %q", hostName, pfx)

				found = true
				break

			}
			if found {
				break ready
			}

			mm, _ := json.MarshalIndent(ings, "", "\t")
			fmt.Printf("listing ingresses:\n%s\n", string(mm))

		case <-timeoutc:
			t.Fatalf("timeout waiting for deployment '%s' to become ready\n", pfx)
		}
	}
}
