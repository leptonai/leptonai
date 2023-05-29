package util

import (
	"crypto/md5"
	"encoding/hex"
	"regexp"
	"strings"
)

const (
	NameInvalidMessage = "Name must consist of lower case alphanumeric characters or '-', and must start with an alphabetical character and end with an alphanumeric character"
)

// HexHash returns the hex encoded md5 hash of the given text.
func HexHash(text []byte) string {
	hash := md5.Sum(text)
	return hex.EncodeToString(hash[:])
}

// JoinByDash joins the given strings with a dash.
func JoinByDash(elem ...string) string {
	return strings.Join(elem, "-")
}

var (
	nameRegex = regexp.MustCompile("^[a-z]([-a-z0-9]*[a-z0-9])?$")
)

// ValidateName returns true if the given name is valid.
func ValidateName(name string) bool {
	return nameRegex.MatchString(name) && len(name) <= 16
}
