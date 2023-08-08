package e2etests

import (
	"fmt"
	"testing"
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
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

		time.Sleep(time.Second)

		// same delete should fail, since the deployment is already deleted
		err = lepton.Deployment().Delete(name)
		if err == nil {
			t.Fatal("expected error for second delete request for the same name, got nil")
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
	return retryUntilNoErrorOrTimeout(15*time.Minute, func() error {
		d, err := lepton.Deployment().Get(id)
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
	if err := waitForDeploymentToRunningState(mainTestDeploymentName); err != nil {
		t.Fatal(err)
	}

	es, err := lepton.Event().GetDeploymentEvents(mainTestDeploymentName)
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

func TestDeploymentOutOfQuota(t *testing.T) {
	patch := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
		Name: mainTestDeploymentName,
		ResourceRequirement: leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
			MinReplicas:   100,
			ResourceShape: leptonaiv1alpha1.GP1HiddenTest,
		},
	}
	_, err := lepton.Deployment().Update(patch)
	if err == nil {
		t.Error("update expecting out of quota error, got nil")
	}

	dName := newName(t.Name())
	d := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
		Name:     dName,
		PhotonID: mainTestPhotonID,
		ResourceRequirement: leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
			ResourceShape: leptonaiv1alpha1.GP1Large,
			MinReplicas:   20,
		},
	}
	_, err = lepton.Deployment().Create(d)
	if err == nil {
		t.Error("create expecting out of quota error, got nil")
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
	if err := waitForDeploymentToRunningState(mainTestDeploymentName); err != nil {
		return err
	}
	// Check that the deployment has numReplicas replicas in running state
	d, err = lepton.Deployment().Get(mainTestDeploymentName)
	if err != nil {
		return err
	}
	if d.ResourceRequirement.MinReplicas != numReplicas {
		return fmt.Errorf("Expected deployment to have %d replicas when running, got %d", numReplicas, d.ResourceRequirement.MinReplicas)
	}
	// Verify there are numReplicas replicas
	return retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		replicas, err := lepton.Replica().List(mainTestDeploymentName)
		if err != nil {
			return fmt.Errorf("Failed to list replicas: %v", err)
		}
		if len(replicas) != int(numReplicas) {
			return fmt.Errorf("Expected deployment to have %d replicas, got %d", numReplicas, len(replicas))
		}
		return nil
	})
}

func TestDeployWithInvalidEnvVar(t *testing.T) {
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
		Envs: []leptonaiv1alpha1.EnvVar{
			{
				Name:  "LEPTON_TEST",
				Value: "test",
			},
		},
	}
	if _, err := lepton.Deployment().Create(d); err == nil {
		t.Fatalf("Expected error when deploying with invalid env var, got nil")
	}

	d.Envs[0].Name = "lepton_test"
	if _, err := lepton.Deployment().Create(d); err == nil {
		t.Fatalf("Expected error when deploying with invalid env var, got nil")
	}

	d.Envs[0].Name = "lEPton_test"
	if _, err := lepton.Deployment().Create(d); err == nil {
		t.Fatalf("Expected error when deploying with invalid env var, got nil")
	}
}

func TestDeleteAndImmediateRecreateWithTheSameName(t *testing.T) {
	dname := newName(t.Name())
	d := &leptonaiv1alpha1.LeptonDeploymentUserSpec{
		Name:     dname,
		PhotonID: mainTestPhotonID,
		ResourceRequirement: leptonaiv1alpha1.LeptonDeploymentResourceRequirement{
			ResourceShape: leptonaiv1alpha1.GP1HiddenTest,
			MinReplicas:   1,
		},
	}
	_, err := lepton.Deployment().Create(d)
	if err != nil {
		t.Fatalf("Failed to create deployment: %v", err)
	}
	err = waitForDeploymentToRunningState(dname)
	if err != nil {
		t.Fatalf("Failed to wait for deployment to running state: %v", err)
	}
	err = lepton.Deployment().Delete(dname)
	if err != nil {
		t.Fatalf("Failed to delete deployment: %v", err)
	}
	err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		_, err := lepton.Deployment().Create(d)
		return err
	})
	if err != nil {
		t.Fatalf("Failed to recreate deployment: %v", err)
	}
	err = waitForDeploymentToRunningState(dname)
	if err != nil {
		t.Fatalf("Failed to wait for deployment to running state: %v", err)
	}
	err = lepton.Deployment().Delete(dname)
	if err != nil {
		t.Fatalf("Failed to delete deployment: %v", err)
	}
}

func TestCustomizedImage(t *testing.T) {
	name := newName(t.Name())
	fullArgs := []string{"pho", "create", "-n", name, "-m", "py:../sdk/leptonai/examples/self_defined_image/main.py:Counter"}
	output, err := client.Run(fullArgs...)
	if err != nil {
		t.Fatalf("Failed to create photon with customized image: %v - %s", err, output)
	}

	fullArgs = []string{"pho", "push", "-n", name}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatalf("Failed to push photon with customized image: %v - %s", err, output)
	}

	fullArgs = []string{"pho", "run", "-n", name}
	output, err = client.Run(fullArgs...)
	if err != nil {
		t.Fatalf("Failed to run photon with customized image: %v - %s", err, output)
	}

	err = waitForDeploymentToRunningState(name)
	if err != nil {
		t.Fatalf("Failed to wait for deployment to running state: %v", err)
	}
	err = lepton.Deployment().Delete(name)
	if err != nil {
		t.Fatalf("Failed to delete deployment: %v", err)
	}
}
