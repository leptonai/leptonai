package main

import (
	"crypto/md5"
	"encoding/hex"
	"regexp"
	"strings"
)

func hash(text []byte) string {
	hash := md5.Sum(text)
	return hex.EncodeToString(hash[:])
}

func joinNameByDash(elem ...string) string {
	return strings.Join(elem, "-")
}

var (
	nameRegex             = regexp.MustCompile("^[a-z]([-a-z0-9]*[a-z0-9])?$")
	nameValidationMessage = "Name must consist of lower case alphanumeric characters or '-', and must start with an alphabetical character and end with an alphanumeric character"
)

func validateName(name string) bool {
	return nameRegex.MatchString(name) && len(name) <= 16
}
