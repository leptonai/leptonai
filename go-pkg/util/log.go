package util

import (
	"context"
	"strings"

	"go.uber.org/zap"
)

var (
	Logger *leptonLogger
)

func init() {
	l, _ := zap.NewProduction()
	Logger = &leptonLogger{
		l.Sugar(),
	}
}

type leptonLogger struct {
	*zap.SugaredLogger
}

// Override the default logger's Errorw func to down level context canceled error
func (l *leptonLogger) Errorw(msg string, keysAndValues ...interface{}) {
	for i := 0; i < len(keysAndValues); i += 2 {
		if keysAndValues[i] != "error" {
			continue
		}
		if err, ok := keysAndValues[i+1].(error); ok {
			if strings.Contains(err.Error(), context.Canceled.Error()) {
				l.SugaredLogger.Warnw(msg, keysAndValues...)
				return
			}
		}
	}

	l.SugaredLogger.Errorw(msg, keysAndValues...)
}
