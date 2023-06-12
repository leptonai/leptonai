package e2etests

import "testing"

func TestClusterInfo(t *testing.T) {
	info, err := lepton.Cluster().Info()
	if err != nil {
		t.Fatal(err)
	}
	if info.BuildTime == "" {
		t.Fatal("BuildTime is empty")
	}
	if info.GitCommit == "" {
		t.Fatal("GitCommit is empty")
	}
	if info.ClusterName == "" {
		t.Fatal("ClusterName is empty")
	}
}
