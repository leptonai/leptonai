package util

import "strings"

// IsSysWorkspace returns true if the given workspace name is a system workspace.
func IsSysWorkspace(name string) bool {
	return strings.HasSuffix(name, "sys")
}
