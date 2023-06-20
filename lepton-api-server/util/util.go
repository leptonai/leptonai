package util

import (
	"crypto/md5"
	"encoding/base32"
	"regexp"
	"strings"

	"github.com/leptonai/lepton/go-pkg/k8s/secret"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	corev1 "k8s.io/api/core/v1"
)

const (
	NameInvalidMessage = "Name must consist of lower case alphanumeric characters or '-', and must start with an alphabetical character and end with an alphanumeric character"
)

// HexHash returns the hex encoded md5 hash of the given text.
func HexHash(text []byte) string {
	hash := md5.Sum(text)
	return strings.ToLower(base32.HexEncoding.EncodeToString(hash[:])[0:8])
}

var (
	nameRegex = regexp.MustCompile("^[a-z]([-a-z0-9]*[a-z0-9])?$")
)

// ValidateName returns true if the given name is valid.
func ValidateName(name string) bool {
	return nameRegex.MatchString(name) && len(name) <= 32
}

func ToContainerEnv(envs []leptonaiv1alpha1.EnvVar) []corev1.EnvVar {
	cenvs := make([]corev1.EnvVar, 0, len(envs))
	for _, env := range envs {
		if env.Value == "" && env.ValueFrom.SecretNameRef == "" {
			continue
		}
		if env.ValueFrom.SecretNameRef != "" {
			cenvs = append(cenvs, corev1.EnvVar{
				Name: env.Name,
				ValueFrom: &corev1.EnvVarSource{
					SecretKeyRef: &corev1.SecretKeySelector{
						LocalObjectReference: corev1.LocalObjectReference{
							Name: secret.SecretObjectName,
						},
						Key: env.ValueFrom.SecretNameRef,
					},
				},
			})
		} else {
			// allow empty value if valueFrom.SecretNameRef is not set
			cenvs = append(cenvs, corev1.EnvVar{
				Name:  env.Name,
				Value: env.Value,
			})
		}
	}
	return cenvs
}
