package util

import "strings"

// UpdateDefaultRegistry updates the given registry for the image URI.
// It replaces the registry part of the image URI with the default registry if
// the image URI does not contain a customized registry.
func UpdateDefaultRegistry(imageURI, registry string) string {
	defaultRegistry := "default"
	if strings.HasPrefix(imageURI, defaultRegistry+"/") {
		return strings.Replace(imageURI, defaultRegistry, registry, 1)
	}

	// legacy default registry
	defaultRegistry = "605454121064.dkr.ecr.us-east-1.amazonaws.com"
	if strings.HasPrefix(imageURI, defaultRegistry+"/") {
		return strings.Replace(imageURI, defaultRegistry, registry, 1)
	}

	return imageURI
}
