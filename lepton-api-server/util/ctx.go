package util

import (
	"context"
	"time"

	"github.com/gin-gonic/gin"
)

const (
	RequestTimeoutInternalCtxKey  = "request-timeout-internal"
	DefaultRequestTimeoutInternal = time.Minute
)

// Sets the value in the gin context for the key "request-timeout-internal".
func SetRequestTimeoutInternal(c *gin.Context, d time.Duration) {
	c.Set(RequestTimeoutInternalCtxKey, d)
}

// Reads the value from the gin context for the key "request-timeout-internal".
func ReadRequestTimetoutInternal(c *gin.Context) time.Duration {
	d := c.GetDuration(RequestTimeoutInternalCtxKey)
	if d == 0 {
		d = DefaultRequestTimeoutInternal
	}
	return d
}

// Small helper to create context and cancel func by deriving
// request timeouts from the gin context.
func CreateCtxFromGinCtx(c *gin.Context) (context.Context, context.CancelFunc) {
	d := ReadRequestTimetoutInternal(c)
	return context.WithTimeout(context.Background(), d)
}
