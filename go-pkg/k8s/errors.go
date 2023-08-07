package k8s

import "strings"

// IsPodInitializingError checks if the error is a pod initializing error
func IsPodInitializingError(err error) bool {
	if err == nil {
		return false
	}
	return strings.Contains(err.Error(), "waiting to start: PodInitializing")
}
