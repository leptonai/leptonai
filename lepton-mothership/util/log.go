package util

import "go.uber.org/zap"

var (
	Logger *zap.SugaredLogger
)

func init() {
	l, _ := zap.NewProduction()
	Logger = l.Sugar()
}
