package v1alpha1

import (
	"testing"

	"k8s.io/utils/ptr"
)

func TestSpecHash(t *testing.T) {
	ld := &LeptonDeployment{
		Spec: LeptonDeploymentSpec{
			LeptonDeploymentUserSpec: LeptonDeploymentUserSpec{
				Name: "test",
			},
		},
	}
	probe = nil
	hash := ld.SpecHash()
	expected := "7d95bb485d"
	if hash != expected {
		t.Errorf("expected %s, got %s", expected, hash)
	}
}

func TestSpecHashWithProbe(t *testing.T) {
	ld := &LeptonDeployment{
		Spec: LeptonDeploymentSpec{
			LeptonDeploymentUserSpec: LeptonDeploymentUserSpec{
				Name: "test",
			},
		},
	}
	probes := []*int{nil, ptr.To[int](0), ptr.To[int](1), ptr.To[int](2)}
	hashes := []string{}
	for _, p := range probes {
		probe = p
		hashes = append(hashes, ld.SpecHash())
	}

	for i := 0; i < len(hashes); i++ {
		for j := i + 1; j < len(hashes); j++ {
			if hashes[i] == hashes[j] {
				t.Errorf("expected different hashes for %d and %d, got %s and %s", i, j, hashes[i], hashes[j])
			}
		}
	}

}
