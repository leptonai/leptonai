package util

import (
	"context"
	"testing"
)

func TestLeptonLogger(t *testing.T) {
	// no panic
	// manually checked the output is right
	// {"level":"warn","ts":1691789339.500128,"caller":"util/log.go:33","msg":"test","error":"context canceled"}
	Logger.Errorw("test", "error", context.Canceled)
}
