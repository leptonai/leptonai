package httperrors

import (
	"errors"
	"testing"
)

func TestIsClientConnectionLost(t *testing.T) {
	err := errors.New("http2: client connection lost")
	if !IsClientConnectionLost(err) {
		t.Error("IsClientConnectionLost should return true")
	}
}
