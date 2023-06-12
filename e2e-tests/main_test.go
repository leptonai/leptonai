package e2etests

import (
	"flag"
	"log"
	"math/rand"
	"os"
	"strings"
	"testing"
	"time"

	e2eutil "github.com/leptonai/lepton/e2e-tests/e2e-util"
	goclient "github.com/leptonai/lepton/go-client"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

var (
	remoteURL = flag.String("remote-url", "", "Remote URL for the Lepton API server")

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

func prepare() {
	flag.Parse()
	lepton = goclient.New(*remoteURL)
	client = e2eutil.NewCliWrapper(*remoteURL)
	mainTestPhotonName = newName("main-test-photon")
	mainTestDeploymentName = newName("main-test-deploy")
	mustPrepareTest()
}

func teardown() {
	mustTeardownTest()
}

func mustPrepareTest() {
	// Create a photon
	_, err := client.RunLocal("photon", "create", "-n", mainTestPhotonName, "-m", "hf:gpt2")
	if err != nil {
		log.Fatal("Failed to create photon ", err)
	}
	_, err = client.RunRemote("photon", "push", "-n", mainTestPhotonName)
	if err != nil {
		log.Fatal("Failed to push photon ", err)
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
			CPU:         2,
			Memory:      2048,
			MinReplicas: 1,
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

var seededRand = rand.New(rand.NewSource(time.Now().UnixNano()))

const (
	charset      = "abcdefghijklmnopqrstuvwxyz"
	nameLenLimit = 32
)

func randString(length int) string {
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[seededRand.Intn(len(charset))]
	}
	return string(b)
}

func newName(testName string) string {
	name := strings.ToLower(testName) + "-" + randString(6)
	// the server limits name lenght to 32
	if len(name) > nameLenLimit {
		name = name[len(name)-nameLenLimit:]
	}
	return name
}
