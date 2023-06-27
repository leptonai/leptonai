package worker

import (
	"context"
	"strings"
	"sync"
	"time"

	"github.com/leptonai/lepton/go-pkg/util"
)

type Job struct {
	f          func(chan<- string) error
	cancelFunc func()
	ctx        context.Context

	wg           *sync.WaitGroup
	failureCount int

	logs  []string
	logMu sync.Mutex
	logCh chan string
}

// NewJob creates a new job. It takes a `chan string` as a parameter,
// which is used to expose the log to the caller.
func NewJob(ctx context.Context, f func(chan<- string) error, cancelFunc func()) *Job {
	job := &Job{
		f:          f,
		cancelFunc: cancelFunc,
		ctx:        ctx,
		wg:         &sync.WaitGroup{},
		logs:       make([]string, 0),
		logCh:      make(chan string, 1000),
	}
	job.wg.Add(2)
	go job.run()
	return job
}

func (j *Job) Wait() {
	j.wg.Wait()
}

func (j *Job) GetLog() string {
	j.logMu.Lock()
	defer j.logMu.Unlock()
	return strings.Join(j.logs, "")
}

func (j *Job) run() {
	go func() {
		// TODO performance of the log array
		for log := range j.logCh {
			j.logMu.Lock()
			j.logs = append(j.logs, log)
			// If the log is too long, truncate it.
			if len(j.logs) > 5000 {
				j.logs = j.logs[len(j.logs)-5000:]
			}
			j.logMu.Unlock()
		}
		j.wg.Done()
	}()
	for {
		select {
		case <-j.ctx.Done():
			j.cancelFunc()
			close(j.logCh)
			j.wg.Done()
			return
		// exponential backoff with an upper limit of 120 seconds
		case <-time.After(time.Duration(util.MinInt(j.failureCount*j.failureCount, 12)) * 10 * time.Second):
			if err := j.f(j.logCh); err == nil {
				close(j.logCh)
				j.wg.Done()
				return
			}
			j.failureCount++
		}
	}
}
