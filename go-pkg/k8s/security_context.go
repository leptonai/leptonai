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

const (
	HomePathNonRoot = "/nonexistent"
	HomeVolumeName  = "home"
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

// RootContainerSecurityContext returns a restricted security context running as root for a container.
func RootContainerSecurityContext() *corev1.SecurityContext {
	return &corev1.SecurityContext{
		AllowPrivilegeEscalation: &falseBool,
		Capabilities: &corev1.Capabilities{
			Add: []corev1.Capability{
				"SETGID",
				"SETUID",
				"FOWNER",
				"CHOWN",
				"DAC_OVERRIDE",
			},
			Drop: []corev1.Capability{"ALL"},
		},
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

// WorkingDirVolumeForNonRoot returns a volume for the working directory for a non-root container.
func WorkingDirVolumeForNonRoot() corev1.Volume {
	return corev1.Volume{
		Name: HomeVolumeName,
		VolumeSource: corev1.VolumeSource{
			EmptyDir: &corev1.EmptyDirVolumeSource{},
		},
	}
}

// WorkingDirVolumeMountForNonRoot returns a volume mount for the working directory for a non-root container.
func WorkingDirVolumeMountForNonRoot() corev1.VolumeMount {
	return corev1.VolumeMount{
		Name:      HomeVolumeName,
		MountPath: HomePathNonRoot,
	}
}