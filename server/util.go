package main

import (
	"crypto/md5"
	"encoding/hex"
	"strings"
)

func hash(text []byte) string {
	hash := md5.Sum(text)
	return hex.EncodeToString(hash[:])
}

func joinNameByDash(elem ...string) string {
	return strings.Join(elem, "-")
}
