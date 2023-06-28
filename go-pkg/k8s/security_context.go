package k8s

import (
	corev1 "k8s.io/api/core/v1"
)

var (
	trueBool  = true
	falseBool = false
	userID    = int64(65534)
	groupID   = int64(65534)
	fsGroup   = int64(65534)
)

// DefaultContainerSecurityContext returns a default restricted security context for a container.
func DefaultContainerSecurityContext() *corev1.SecurityContext {
	return &corev1.SecurityContext{
		RunAsUser:                &userID,
		RunAsGroup:               &groupID,
		AllowPrivilegeEscalation: &falseBool,
		Capabilities: &corev1.Capabilities{
			Drop: []corev1.Capability{"ALL"},
		},
		RunAsNonRoot: &trueBool,
		SeccompProfile: &corev1.SeccompProfile{
			Type: corev1.SeccompProfileTypeRuntimeDefault,
		},
	}
}

// DefaultPodSecurityContext returns a default security context for a pod with the default FS Group.
func DefaultPodSecurityContext() *corev1.PodSecurityContext {
	return &corev1.PodSecurityContext{
		FSGroup: &fsGroup,
	}
}
