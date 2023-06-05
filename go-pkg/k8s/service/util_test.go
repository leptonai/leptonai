package service

import "testing"

func TestServiceName(t *testing.T) {
	if ServiceName("test") != "test-service" {
		t.Error("ServiceName failed")
	}
}
