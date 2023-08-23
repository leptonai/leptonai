package e2etests

import (
	"bytes"
	"fmt"
	"net/url"
	"testing"
	"time"

	"golang.org/x/net/websocket"
)

func TestListReplica(t *testing.T) {
	err := retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		replicas, err := lepton.Replica().List(mainTestDeploymentName)
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
		replicas, err := lepton.Replica().List(mainTestDeploymentName)
		if err != nil {
			t.Fatal(err)
		}
		if len(replicas) != 1 {
			return fmt.Errorf("expected 1 replica, got %d", len(replicas))
		}
		rid := replicas[0].ID
		_, err = lepton.Replica().Shell(mainTestDeploymentName, rid)
		if err != nil {
			return err
		}
		return nil
	})
	if err != nil {
		t.Fatalf("failed to get replica shell: %v", err)
	}
}

func TestReplicaShellQueryString(t *testing.T) {
	replicas, err := lepton.Replica().List(mainTestDeploymentName)
	if err != nil {
		t.Fatal(err)
	}
	rid := replicas[0].ID
	shellURL := client.WorkspaceURL + "/deployments/" + mainTestDeploymentName + "/replicas/" + rid + "/shell" + "?access_token=" + *authToken
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
	replicas, err := lepton.Replica().List(mainTestDeploymentName)
	if err != nil {
		t.Fatal(err)
	}
	rid := replicas[0].ID
	err = retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		log, _ := lepton.Replica().Log(mainTestDeploymentName, rid, 4096, 5)
		// do not check error as long as the content has the required substring:
		// error is expected since it's a long running process
		// e.g., "... (Press CTRL+C to quit)", or context deadline exceeded
		if len(log) == 0 {
			return fmt.Errorf("expected log to be non-empty, got %d", len(log))
		}
		if !bytes.Contains(log, []byte("running on http")) {
			return fmt.Errorf("expected log to contain 'INFO', got %s", string(log))
		}
		return nil
	})
	if err != nil {
		t.Fatalf("failed to get replica log: %v", err)
	}
}
