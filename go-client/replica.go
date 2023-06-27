package goclient

import (
	"encoding/json"
	"net/http"
	"net/url"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"golang.org/x/net/websocket"
)

const replicasPath = "/replicas"

type Replica struct {
	Lepton
}

func (l *Replica) List(deploymentID string) ([]httpapi.Replica, error) {
	output, err := l.HTTP.RequestPath(http.MethodGet, deploymentsPath+"/"+deploymentID+replicasPath, nil, nil)
	if err != nil {
		return nil, err
	}
	ret := []httpapi.Replica{}
	if err := json.Unmarshal(output, &ret); err != nil {
		return nil, err
	}
	return ret, nil
}

// TODO: refactor this to return a meaningful message instead of a single byte
// quick implementation to test the websocket connection
func (l *Replica) Shell(deploymentID string, replicaID string) ([]byte, error) {
	shellURL := l.HTTP.RemoteURL + deploymentsPath + "/" + deploymentID + replicasPath + "/" + replicaID + "/shell"
	u, err := url.Parse(shellURL)
	if err != nil {
		return nil, err
	}

	prefix := "ws://"
	if u.Scheme == "https" {
		prefix = "wss://"
	}
	url := prefix + u.Host + u.RequestURI()
	origin := u.Scheme + "://" + u.Host

	wsConfig, err := websocket.NewConfig(url, origin)
	if err != nil {
		return nil, err
	}

	for k := range l.HTTP.Header {
		wsConfig.Header.Add(k, l.HTTP.Header.Get(k))
	}

	ws, err := websocket.DialConfig(wsConfig)
	if err != nil {
		return nil, err
	}
	defer ws.Close()

	err = websocket.Message.Send(ws, "ls\n")
	if err != nil {
		return nil, err
	}

	var msg = make([]byte, 512)

	if err := websocket.Message.Receive(ws, &msg); err != nil {
		return nil, err
	}
	return msg, nil
}

// TODO: log
