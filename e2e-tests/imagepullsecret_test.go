package e2etests

import "testing"

func TestImagePullSecret(t *testing.T) {
	ipsname := "test-imagepull-secret"

	err := lepton.ImagePullSecret().Create(ipsname,
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

	found := false
	for i := range ips {
		if ips[i].Metadata.Name == ipsname {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Expected image pull secret %s, got %v", ipsname, ips)
	}
	t.Logf("Got image pull secret: %s", ips[0].Metadata.Name)

	err = lepton.ImagePullSecret().Delete(ipsname)
	if err != nil {
		t.Fatal(err)
	}

	ips, err = lepton.ImagePullSecret().List()
	if err != nil {
		t.Fatal(err)
	}
	found = false
	for i := range ips {
		if ips[i].Metadata.Name == ipsname {
			found = true
			break
		}
	}
	if found {
		t.Errorf("Not expected image pull secret %s, got %v", ipsname, ips)
	}
}
