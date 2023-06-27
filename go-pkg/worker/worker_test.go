package worker

import (
	"testing"
	"time"
)

func TestWorker(t *testing.T) {
	w := New()
	jobName := "test"
	if err := w.CreateJob(2*time.Second, jobName, func(logCh chan<- string) error {
		time.Sleep(time.Second)
		return nil
	}, func() {}); err != nil {
		t.Errorf("Worker.CreateJob(\"test\", func(log chan string) error { return nil }) = %v; want nil", err)
	}
	job := w.GetJob(jobName)
	if job == nil {
		t.Errorf("Worker.GetJob(\"test\") = nil; want not nil")
	}
	job.Wait()
}
