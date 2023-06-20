package e2etests

import (
	"fmt"
	"net/url"
	"testing"
	"time"

	"golang.org/x/net/websocket"
)

func TestListInstance(t *testing.T) {
	err := retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		instances, err := lepton.Instance().List(mainTestDeploymentID)
		if err != nil {
			t.Fatal(err)
		}
		if len(instances) != 1 {
			return fmt.Errorf("expected 1 instance, got %d", len(instances))
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestInstanceShell(t *testing.T) {
	err := retryUntilNoErrorOrTimeout(2*time.Minute, func() error {
		instances, err := lepton.Instance().List(mainTestDeploymentID)
		if err != nil {
			t.Fatal(err)
		}
		iid := instances[0].ID
		_, err = lepton.Instance().Shell(mainTestDeploymentID, iid)
		if err != nil {
			return err
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestInstanceShellQueryString(t *testing.T) {
	instances, err := lepton.Instance().List(mainTestDeploymentID)
	if err != nil {
		t.Fatal(err)
	}
	iid := instances[0].ID
	shellURL := client.RemoteURL + "/deployments/" + mainTestDeploymentID + "/instances/" + iid + "/shell" + "?access_token=" + *authToken
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

func TestInstanceLog(t *testing.T) {
	// TODO: implement log in go-client first
}
