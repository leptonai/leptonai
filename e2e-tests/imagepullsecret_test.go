package e2etests

import "testing"

func TestImagePullSecret(t *testing.T) {
	err := lepton.ImagePullSecret().Create("test-imagepull-secret",
		"test-registry",
		"test-username",
		"test-password",
		"test-email")

	if err != nil {
		t.Fatal(err)
	}

	ips, err := lepton.ImagePullSecret().List()
	if err != nil {
		t.Fatal(err)
	}

	if len(ips) != 1 {
		t.Fatal("Expected 1 image pull secret, got 0")
	}
	t.Logf("Got image pull secret: %s", ips[0].Metadata.Name)

	err = lepton.ImagePullSecret().Delete("test-imagepull-secret")
	if err != nil {
		t.Fatal(err)
	}

	ips, err = lepton.ImagePullSecret().List()
	if err != nil {
		t.Fatal(err)
	}
	if len(ips) != 0 {
		t.Errorf("Expected 0 image pull secret, got %d", len(ips))
		for i := range ips {
			t.Errorf("	Got Image pull secret %s", ips[i].Metadata.Name)
		}
	}
}
