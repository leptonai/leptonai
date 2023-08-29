package controller

import (
	"sync"
	"testing"
)

func TestDrainChan(t *testing.T) {
	n := 10
	ch := make(chan struct{}, n)
	for i := 0; i < n; i++ {
		ch <- struct{}{}
	}
	drainChan(ch)
	select {
	case <-ch:
		t.Error("channel should be drained")
	default:
	}
}

func TestSleepAndPoke(t *testing.T) {
	ch := make(chan struct{}, 1)
	wg := &sync.WaitGroup{}
	wg.Add(1)
	go backoffAndRetry(wg, ch)
	select {
	case <-ch:
		t.Error("channel should not be poked yet")
	default:
	}
	wg.Wait()
	<-ch
}

func TestCompareLeptonDeploymentSpecHash(t *testing.T) {
	tests := []struct {
		a map[string]string
		b map[string]string
		e bool
	}{
		{nil, nil, false},
		{nil, map[string]string{}, false},
		{map[string]string{}, nil, false},
		{map[string]string{}, map[string]string{}, true},
		{map[string]string{"a": "a"}, map[string]string{"a": "a"}, true},
		{map[string]string{leptonDeploymentSpecHashKey: "a"}, map[string]string{"a": "a"}, false},
		{map[string]string{"a": "a"}, map[string]string{leptonDeploymentSpecHashKey: "b"}, false},
		{map[string]string{leptonDeploymentSpecHashKey: "a"}, map[string]string{leptonDeploymentSpecHashKey: "b"}, false},
		{map[string]string{leptonDeploymentSpecHashKey: "b"}, map[string]string{leptonDeploymentSpecHashKey: "b"}, true},
	}

	for i, test := range tests {
		if compareLeptonDeploymentSpecHash(test.a, test.b) != test.e {
			t.Errorf("expected %t for tesi %d: %+v, got %t", test.e, i, test, !test.e)
		}
	}
}
