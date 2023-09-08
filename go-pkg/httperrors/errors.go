package httperrors

import "strings"

const (
	ErrorCodeInternalFailure  = "InternalFailure"
	ErrorCodeInvalidRequest   = "InvalidRequest"
	ErrorCodeValidationError  = "ValidationError"
	ErrorCodeResourceNotFound = "ResourceNotFound"
	ErrorCodeResourceConflict = "ResourceConflict"
	ErrorCodeRequestTimeout   = "RequestTimeout"
)

// IsClientConnectionLost checks if the error is caused by client connection lost.
func IsClientConnectionLost(err error) bool {
	return strings.Contains(err.Error(), "client connection lost")
}
