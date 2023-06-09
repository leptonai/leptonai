package e2etests

import (
	"encoding/json"
	"net/http"
	"testing"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
)

func TestClusterInfo(t *testing.T) {
	req, err := http.NewRequest(http.MethodGet, *remoteURL+"/cluster", nil)
	if err != nil {
		t.Fatal(err)
	}
	b, err := checkOKHTTP(&http.Client{}, req, nil)
	if err != nil {
		t.Fatal(err)
	}

	ci := &httpapi.ClusterInfo{}
	if err := json.Unmarshal(b, ci); err != nil {
		t.Fatal(err)
	}
	t.Logf("cluster info %+v", ci)

	if ci.BuildTime == "" {
		t.Fatal("unexpected empty build time")
	}
	if ci.GitCommit == "" {
		t.Fatal("unexpected empty git commit")
	}
}
