package datastore

import (
	"fmt"
	"time"

	goutil "github.com/leptonai/lepton/go-pkg/util"
)

const (
	// warning if an operation takes longer than this
	warningDuration = 1 * time.Second
	// error if an operation takes longer than this
	errorDuration = 3 * time.Second
)

func maybeLogTookTooLong(op, kind, ns string, st time.Time) {
	if time.Since(st) > errorDuration {
		goutil.Logger.Errorw(fmt.Sprintf("operation took too long: %v", time.Since(st)),
			"operation", op,
			"kind", kind,
			"namespace", ns,
		)
		return
	}
	if time.Since(st) > warningDuration {
		goutil.Logger.Warnw(fmt.Sprintf("operation took too long: %v", time.Since(st)),
			"operation", op,
			"kind", kind,
			"namespace", ns,
		)
		return
	}
}
