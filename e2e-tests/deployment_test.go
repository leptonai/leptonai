package e2etests

import (
	"fmt"
	"testing"
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

func TestDeploySamePhotonMultipleTimes(t *testing.T) {
	numTests := 3
	dNames := []string{}
	// Create deployments
	for i := 0; i < numTests; i++ {
		dName := newName(t.Name())
		dNames = append(dNames, dName)
		d := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
			Name:     dName,
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
			t.Fatal(err)
		}
		if ld.Name != dName {
			t.Fatal("Expected deployment name to be ", dName, ", got ", ld.Name)
		}
		if ld.ID != dName {
			t.Fatal("Expected deployment ID to be ", dName, ", got ", ld.ID)
		}
	}
	// Sleep for a bit to let the server reconcile
	time.Sleep(time.Second)
	// Check that deployments exist
	ds, err := lepton.Deployment().List()
	if err != nil {
		t.Fatal(err)
	}
	if len(ds) < numTests {
		t.Fatal("Expected at least ", numTests, " deployments, got ", len(ds))
	}
	// Delete deployments
	for _, name := range dNames {
		err = lepton.Deployment().Delete(name)
		if err != nil {
			t.Fatal(err)
		}
	}
}

func TestDeployWithDuplicateName(t *testing.T) {
	dName := newName(t.Name())
	d := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
		Name:     dName,
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
		t.Fatal(err)
	}
	if ld.Name != dName {
		t.Fatal("Expected deployment name to be ", dName, ", got ", ld.Name)
	}
	if ld.ID != dName {
		t.Fatal("Expected deployment ID to be ", dName, ", got ", ld.ID)
	}
	_, err = lepton.Deployment().Create(d)
	if err == nil {
		t.Fatal("Expected error when deployment with the same name again, got nil")
	}
	err = lepton.Deployment().Delete(dName)
	if err != nil {
		t.Fatal(err)
	}
}

func waitForDeploymentToRunningState(id string) error {
	return retryUntilNoErrorOrTimeout(10*time.Minute, func() error {
		d, err := lepton.Deployment().Get(mainTestDeploymentID)
		if err != nil {
			return err
		}
		if d.Status.State != "Running" {
			return fmt.Errorf("Expected deployment to be in Running state, got %s", d.Status.State)
		}
		if d.Status.Endpoint.ExternalEndpoint == "" {
			return fmt.Errorf("Expected deployment to have an external endpoint, got empty string")
		}
		return nil
	})
}

func TestDeploymentStatusAndEvents(t *testing.T) {
	if err := waitForDeploymentToRunningState(mainTestDeploymentID); err != nil {
		t.Fatal(err)
	}

	es, err := lepton.Event().GetDeploymentEvents(mainTestDeploymentID)
	if err != nil {
		t.Fatal(err)
	}
	if len(es) == 0 {
		t.Fatalf("Expected deployment to have at least one event, got %d", len(es))
	}
	t.Log("Deployment events:", es[0].Reason)
}

func TestUpdateDeploymentMinReplicas(t *testing.T) {
	// Update deployment to have 2 replicas
	if err := updateAndVerifyDeploymentMinReplicas(mainTestDeploymentName, 2); err != nil {
		t.Fatal(err)
	}
	// Patch back to 1 replica to not hurt other tests
	if err := updateAndVerifyDeploymentMinReplicas(mainTestDeploymentName, 1); err != nil {
		t.Fatal(err)
	}
}

func updateAndVerifyDeploymentMinReplicas(name string, numReplicas int32) error {
	patch := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
		Name: mainTestDeploymentName,
		ResourceRequirement: leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
			MinReplicas: numReplicas,
		},
	}
	d, err := lepton.Deployment().Update(patch)
	if err != nil {
		return err
	}
	if d.ResourceRequirement.MinReplicas != numReplicas {
		return fmt.Errorf("Expected deployment to have %d replicas in patch response, got %d", numReplicas, d.ResourceRequirement.MinReplicas)
	}
	// Wait for deployment to be running
	if err := waitForDeploymentToRunningState(mainTestDeploymentID); err != nil {
		return err
	}
	// Check that the deployment has numReplicas replicas in running state
	d, err = lepton.Deployment().Get(mainTestDeploymentID)
	if err != nil {
		return err
	}
	if d.ResourceRequirement.MinReplicas != numReplicas {
		return fmt.Errorf("Expected deployment to have %d replicas when running, got %d", numReplicas, d.ResourceRequirement.MinReplicas)
	}
	// Verify there are numReplicas replicas
	return retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		replicas, err := lepton.Replica().List(mainTestDeploymentID)
		if err != nil {
			return fmt.Errorf("Failed to list replicas: %v", err)
		}
		if len(replicas) != int(numReplicas) {
			return fmt.Errorf("Expected deployment to have %d replicas, got %d", numReplicas, len(replicas))
		}
		return nil
	})
}
