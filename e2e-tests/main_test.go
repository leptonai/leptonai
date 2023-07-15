package e2etests

import (
	"flag"
	"fmt"
	"log"
	"net"
	"net/url"
	"os"
	"strings"
	"testing"
	"time"

	e2eutil "github.com/leptonai/lepton/e2e-tests/e2e-util"
	goclient "github.com/leptonai/lepton/go-client"
	"github.com/leptonai/lepton/go-pkg/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

var (
	workspaceURL = flag.String("workspace-url", "", "URL for the Lepton API server")
	authToken    = flag.String("auth-token", "", "Auth token for the Lepton API server")

	mainTestPhotonName     string
	mainTestPhotonID       string
	mainTestDeploymentName string
	mainTestDeploymentID   string

	lepton *goclient.Lepton
	client *e2eutil.CliWrapper
)

func TestMain(m *testing.M) {
	prepare()
	code := m.Run()
	teardown()
	os.Exit(code)
}

const (
	modelName = "../sdk/leptonai/examples/elements/main.py"
)

func prepare() {
	flag.Parse()
	// Wait for DNS propagation
	endpoint, err := url.Parse(*workspaceURL)
	if err != nil {
		log.Fatal("Expected workspace URL to be a valid URL, got ", *workspaceURL)
	}
	err = waitForDNSPropagation(endpoint.Hostname())
	if err != nil {
		log.Fatal("Expected DNS to propagate for ", endpoint.Hostname(), ", got ", err)
	}
	// Prepare the test
	lepton = goclient.New(*workspaceURL, *authToken)
	client = e2eutil.NewCliWrapper(*workspaceURL, *authToken)
	mainTestPhotonName = newName("main-test-photon")
	mainTestDeploymentName = newName("main-test-deploy")

	mustPrepareTest()
}

func teardown() {
	mustTeardownTest()
}

func mustPrepareTest() {
	// create a photon
	out, err := client.RunLocal("photon", "create", "-n", mainTestPhotonName, "-m", modelName)
	if err != nil {
		log.Fatalf("Failed to create photon %s: %s: %s", mainTestPhotonName, err, out)
	}
	out, err = client.RunRemote("photon", "push", "-n", mainTestPhotonName)
	if err != nil {
		log.Fatalf("Failed to push photon %s: %s: %s", mainTestPhotonName, err, out)
	}
	// Sleep for a bit to let the server reconcile
	time.Sleep(time.Second)
	ph, err := lepton.Photon().GetByName(mainTestPhotonName)
	if err != nil {
		log.Fatal("Failed to get photon by name: ", err)
	}
	if len(ph) != 1 {
		log.Fatal("Expected 1 photon, got ", len(ph))
	}
	mainTestPhotonID = ph[0].ID
	// Create a deployment
	d := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
		Name:     mainTestDeploymentName,
		PhotonID: mainTestPhotonID,
		ResourceRequirement: leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
			ResourceShape: leptonaiv1alpha1.GP1HiddenTest,
			MinReplicas:   1,
		},
		APITokens: []leptonaiv1alpha1.TokenVar{
			{
				ValueFrom: leptonaiv1alpha1.TokenValue{
					TokenNameRef: leptonaiv1alpha1.TokenNameRefWorkspaceToken,
				},
			},
		},
	}
	ld, err := lepton.Deployment().Create(d)
	if err != nil {
		log.Fatal("Failed to create deployment: ", err)
	}
	mainTestDeploymentID = ld.ID
	if mainTestDeploymentID != mainTestDeploymentName {
		log.Fatal("Expected deployment ID to be ", mainTestDeploymentName, ", got ", mainTestDeploymentID)
	}
}

func mustTeardownTest() {
	if err := lepton.Deployment().Delete(mainTestDeploymentID); err != nil {
		log.Fatal("Failed to delete deployment: ", err)
	}
	time.Sleep(time.Second)
	if err := lepton.Photon().Delete(mainTestPhotonID); err != nil {
		log.Fatal("Failed to delete photon: ", err)
	}
}

const (
	nameLenLimit = 32
)

func newName(testName string) string {
	name := strings.ToLower(testName) + "-" + util.RandString(6)
	// the server limits name lenght to 32
	if len(name) > nameLenLimit {
		name = name[len(name)-nameLenLimit:]
	}
	return name
}

func waitForDNSPropagation(hostname string) error {
	return retryUntilNoErrorOrTimeout(10*time.Minute, func() error {
		ips, err := net.LookupIP(hostname)
		log.Printf("hostname: %v, ips: %v, err %v", hostname, ips, err)
		if err != nil {
			return fmt.Errorf("failed to lookup IP for %s: %v", hostname, err)
		}
		if len(ips) == 0 {
			return fmt.Errorf("no IP found for %s", hostname)
		}
		return nil
	})
}

func retryUntilNoErrorOrTimeout(timeout time.Duration, f func() error) error {
	tick := 10 * time.Second
	t := time.After(timeout)
	ticker := time.Tick(tick)
	var err error
	for {
		select {
		case <-ticker:
			err = f()
			if err == nil {
				return nil
			}
			log.Printf("retrying after error: %v", err)
		case <-t:
			return fmt.Errorf("timeout with last error: %v", err)
		}
	}
}
