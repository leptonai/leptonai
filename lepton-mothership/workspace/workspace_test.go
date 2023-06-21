package workspace

import "testing"

func TestEFSMountTarget(t *testing.T) {
	privateSubnets := []string{"subnet-12345678", "subnet-87654321"}
	efsMountTargets := efsMountTargets(privateSubnets)

	expected := `{"az-0"={"subnet_id"="subnet-12345678"},"az-1"={"subnet_id"="subnet-87654321"}}`

	if efsMountTargets != expected {
		t.Errorf("expecting %s, got %s", expected, efsMountTargets)
	}
}
