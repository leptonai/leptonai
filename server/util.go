package main

import (
	"crypto/md5"
	"encoding/hex"
)

func hash(text []byte) string {
	hash := md5.Sum(text)
	return hex.EncodeToString(hash[:])
}

func uniqName(name, uuid string) string {
	return name + "-" + uuid
}
