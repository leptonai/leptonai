package e2etests

import (
	"fmt"
	"net/url"
	"testing"
	"time"

	"golang.org/x/net/websocket"
)

func TestListReplica(t *testing.T) {
	err := retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		replicas, err := lepton.Replica().List(mainTestDeploymentID)
		if err != nil {
			t.Fatal(err)
		}
		if len(replicas) != 1 {
			return fmt.Errorf("expected 1 replica, got %d", len(replicas))
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestReplicaShell(t *testing.T) {
	err := retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		replicas, err := lepton.Replica().List(mainTestDeploymentID)
		if err != nil {
			t.Fatal(err)
		}
		rid := replicas[0].ID
		_, err = lepton.Replica().Shell(mainTestDeploymentID, rid)
		if err != nil {
			return err
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestReplicaShellQueryString(t *testing.T) {
	replicas, err := lepton.Replica().List(mainTestDeploymentID)
	if err != nil {
		t.Fatal(err)
	}
	rid := replicas[0].ID
	shellURL := client.RemoteURL + "/deployments/" + mainTestDeploymentID + "/replicas/" + rid + "/shell" + "?access_token=" + *authToken
	u, err := url.Parse(shellURL)
	if err != nil {
		t.Fatal(err)
	}
	prefix := "ws://"
	if u.Scheme == "https" {
		prefix = "wss://"
	}

	url := prefix + u.Host + u.RequestURI()
	origin := u.Scheme + "://" + u.Host
	ws, err := websocket.Dial(url, "", origin)
	if err != nil {
		t.Fatal(err)
	}
	defer ws.Close()

	err = websocket.Message.Send(ws, "ls\n")
	if err != nil {
		t.Fatal(err)
	}
	var msg = make([]byte, 512)
	if err := websocket.Message.Receive(ws, &msg); err != nil {
		t.Fatal(err)
	}
}

func TestReplicaLog(t *testing.T) {
	// TODO: implement log in go-client first
}
