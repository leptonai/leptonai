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
	go sleepAndPoke(wg, ch)
	select {
	case <-ch:
		t.Error("channel should not be poked yet")
	default:
	}
	wg.Wait()
	<-ch
}
