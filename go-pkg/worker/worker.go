package worker

import (
	"context"
	"fmt"
	"sync"
	"time"
)

type Worker struct {
	jobs map[string]*Job
	mu   sync.Mutex
}

func New() *Worker {
	return &Worker{
		jobs: make(map[string]*Job),
	}
}

// CreateJob creates a new job. It takes a `chan string` as a parameter,
// which is used to expose the log to the caller.
func (w *Worker) CreateJob(timeout time.Duration, name string, f func(chan<- string) error, cancelFunc func()) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if _, ok := w.jobs[name]; ok {
		return fmt.Errorf("job %s exists and is running", name)
	}
	ctx, cencel := context.WithTimeout(context.Background(), timeout)
	job := NewJob(ctx, name, f, cancelFunc)
	w.jobs[name] = job
	go func() {
		job.Wait()
		cencel()
		w.mu.Lock()
		defer w.mu.Unlock()
		// TODO: do not delete, allowing people to see the log
		delete(w.jobs, name)
	}()
	return nil
}

func (w *Worker) GetJob(name string) *Job {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.jobs[name]
}
