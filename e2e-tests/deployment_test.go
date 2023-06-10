package e2etests

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"strings"
	"testing"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"sigs.k8s.io/controller-runtime/pkg/client"

	appsv1 "k8s.io/api/apps/v1"
	networkingv1 "k8s.io/api/networking/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/watch"
)

func TestDeploymentCreateListRemove(t *testing.T) {
	before := mustListDeployment(t)

	phName := "photon-" + randString(5)
	t.Logf("testing photon %q", phName)

	mustCreatePhoton(t, phName)
	mustPushPhoton(t, phName)
	mustDeployPhoton(t, phName)
	deploymentName := mustVerifyDeployment(t, phName)
	t.Logf("found deployment %q in the namespace %q", deploymentName, *namespace)
	if !strings.HasPrefix(deploymentName, "deploy-") {
		t.Fatalf("deployment name %q does not have the expected prefix 'deploy-'", deploymentName)
	}

	// TODO: currently this would not work
	// because the default "photon run" does not specify
	// enough resources for GPT2 models to run
	rootDomain := mustVerifyAPIServerIngress(t)
	t.Logf("found root domain %q in namespace %q", rootDomain, *namespace)
	if len(rootDomain) == 0 {
		t.Fatalf("failed to find root domain")
	}

	start := time.Now()
	timer := time.NewTimer(2 * time.Minute)
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

done:
	for {
		select {
		case <-ticker.C:
			err := checkGPT2API(rootDomain, deploymentName)
			if err != nil {
				t.Logf("failed checkGPT2API %v (so far took %v)", err, time.Since(start))
				continue
			}

			t.Logf("successfully checked GPT2 (took %v)", time.Since(start))
			break done

		case <-timer.C:
			t.Logf("failed to check GPT2 in time")
			break done
		}
	}

	after := mustListDeployment(t)
	if len(after) != len(before)+1 {
		t.Fatalf("after deployment, expected %d+1 deployments but got %d", len(before), len(after))
	}

	pid := getPhotonID(phName, mustListPhoton(t))
	did := mustGetDeploymentIDbyPhotonID(t, pid)
	mustRemoveDeploymentByID(t, did)
	after = mustListDeployment(t)
	if len(after) != len(before) {
		t.Fatalf("after removal, expected %d deployments but got %d", len(before), len(after))
	}
}

func mustDeployPhoton(t *testing.T, name string) {
	id := getPhotonID(name, mustListPhoton(t))

	// currently only tests gpt2 which may require more than 1>CPU
	// TODO: support other models
	cmd := exec.Command("lepton", "photon", "run", "-i", id, "-r", *remoteURL, "--cpu", "2", "--memory", "2024", "--min-replicas", "1")
	out, err := cmd.Output()
	if err != nil {
		fmt.Println(string(out))
		t.Fatal(err)
	}

	// no specific output for "photon run" command runs
}

func mustListDeployment(t *testing.T) []httpapi.LeptonDeployment {
	req, err := http.NewRequest(http.MethodGet, *remoteURL+"/deployments", nil)
	if err != nil {
		t.Fatal(err)
	}
	b, err := checkOKHTTP(&http.Client{}, req, nil)
	if err != nil {
		t.Fatal(err)
	}

	var ds []httpapi.LeptonDeployment
	err = json.NewDecoder(bytes.NewReader(b)).Decode(&ds)
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
	req, err := http.NewRequest(http.MethodDelete, *remoteURL+"/deployments/"+id, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := checkOKHTTP(&http.Client{}, req, nil); err != nil {
		t.Fatal(err)
	}
}

func mustVerifyDeployment(t *testing.T, phName string) (deploymentName string) {
	ch, err := k8s.Client.Watch(
		context.Background(),
		&appsv1.DeploymentList{},
		client.InNamespace(*namespace),
		client.MatchingLabels{"photon_name": phName},
	)
	if err != nil {
		t.Fatal(err)
	}

	tick := time.Tick(5 * time.Second)
	for {
		select {
		case event := <-ch.ResultChan():
			deployment := event.Object.(*appsv1.Deployment)
			t.Logf("Watch deployment event %v for name %q", event.Type, deployment.Name)

			switch event.Type {
			case watch.Added, watch.Modified:
				v, ok := deployment.Labels["photon_name"]
				if ok && v == phName {
					t.Logf("Watch found deployment %q with matching label (ready replicas %d)", deployment.Name, deployment.Status.ReadyReplicas)
					return deployment.Name
				}
			default:
			}
		case <-tick:
			return ""
		}
	}
}

const (
	phPrepareStr             = "lepton photon prepare"
	phRunStr                 = "lepton photon run"
	externalDNSAnnotationKey = "external-dns.alpha.kubernetes.io/hostname"
)

var leptonAPIServerIngressName = ingress.IngressName("lepton-api-server")

// ensure ingress is set up correctly
func mustVerifyAPIServerIngress(t *testing.T) (externalDNS string) {
	ch, err := k8s.Client.Watch(
		context.Background(),
		&networkingv1.IngressList{},
		client.InNamespace(*namespace),
	)
	if err != nil {
		t.Fatal(err)
	}

	tick := time.Tick(5 * time.Second)
	for {
		select {
		case event := <-ch.ResultChan():
			ing := event.Object.(*networkingv1.Ingress)
			t.Logf("Watch ingress event %v for name %q", event.Type, ing.Name)
			if ing.Name != leptonAPIServerIngressName {
				continue
			}
			switch event.Type {
			case watch.Added, watch.Modified:
				hostName := ing.Status.LoadBalancer.Ingress[0].Hostname
				externalDNS = ing.Annotations[externalDNSAnnotationKey]
				t.Logf("Watch found ingress %q with matching name (hostname %q and external DNS %q)", leptonAPIServerIngressName, hostName, externalDNS)
				return externalDNS
			default:
			}
		case <-tick:
			t.Logf("Watch ingress timeout")
			return ""
		}
	}
}

func checkGPT2API(leptonAPIServerDNS string, deploymentName string) error {
	ingressNameForDeployment := ingress.IngressNameForHostBased(deploymentName)
	fmt.Printf("checking the ingress %q in the namespace %q\n", ingressNameForDeployment, *namespace)

	ing := &networkingv1.Ingress{}
	if err := k8s.Client.Get(
		context.Background(),
		types.NamespacedName{
			Name:      ingressNameForDeployment,
			Namespace: *namespace,
		},
		ing); err != nil {
		return err
	}
	if len(ing.Status.LoadBalancer.Ingress) == 0 {
		return errors.New("no ingress found")
	}
	externalDNS := ing.Annotations[externalDNSAnnotationKey]
	if externalDNS == "" {
		return fmt.Errorf("no %q found in annotations %+v", externalDNSAnnotationKey, ing.Annotations)
	}

	apiEndpointFromDeploymentName := fmt.Sprintf("https://%s.%s/run", deploymentName, leptonAPIServerDNS)

	// no need to prefix with deploy name again, since we get the external DNS
	// using "ingress.IngressNameForHostBased"
	apiEndpointFromIngress := fmt.Sprintf("https://%s/run", externalDNS)

	if apiEndpointFromDeploymentName != apiEndpointFromIngress {
		return fmt.Errorf("unexpected api endpoint for gpt2 /run %q (expected %q)", apiEndpointFromIngress, apiEndpointFromDeploymentName)
	}

	url := apiEndpointFromIngress
	fmt.Printf("sending gpt2 /run request to %q\n", url)

	body := []byte(`{"do_sample":true,"inputs":"I enjoy walking with my cute dog","max_length":50,"top_k":50,"top_p":0.95}`)
	headers := map[string]string{
		"deployment":   deploymentName,
		"Content-Type": "application/json",
		"accept":       "application/json",
	}
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	c := &http.Client{
		Timeout: time.Duration(5 * time.Second),

		// TODO: remove this
		// c.f., https://github.com/leptonai/lepton/issues/457
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true,
			},
		},
	}
	r, err := checkOKHTTP(c, req, nil)
	if err != nil {
		return err
	}

	fmt.Println("result:", string(r))
	return nil
}

func checkOKHTTP(c *http.Client, req *http.Request, readFunc func(io.Reader) ([]byte, error)) ([]byte, error) {
	resp, err := c.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected HTTP status code %v", resp.StatusCode)
	}

	if readFunc == nil {
		readFunc = io.ReadAll
	}
	body, err := readFunc(resp.Body)
	if err != nil {
		return nil, err
	}
	return body, nil
}
