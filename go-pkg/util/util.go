package util

import (
	"bufio"
	"bytes"
	"log"
	"math/rand"
	"os"
	"strings"
	"time"
)

var seededRand = rand.New(rand.NewSource(time.Now().UnixNano()))

const (
	charset = "abcdefghijklmnopqrstuvwxyz"
)

func RandString(length int) string {
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[seededRand.Intn(len(charset))]
	}
	return string(b)
}

func MinInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func ContainsString(slice []string, s string) bool {
	for _, item := range slice {
		if item == s {
			return true
		}
	}
	return false
}

func RemoveString(slice []string, s string) (result []string) {
	for _, item := range slice {
		if item == s {
			continue
		}
		result = append(result, item)
	}
	return
}

func UniqStringSlice(slice []string) []string {
	seen := make(map[string]bool)
	uniq := make([]string, 0)
	for _, item := range slice {
		if _, ok := seen[item]; ok {
			continue
		}
		seen[item] = true
		uniq = append(uniq, item)
	}
	return uniq
}

func RemovePrefix(msg string, prefix string) string {
	// remove the prefix from all words in the message
	// return the new message
	words := strings.Split(msg, " ")
	for i := range words {
		words[i] = strings.TrimPrefix(words[i], prefix)
	}
	return strings.Join(words, " ")
}

// deepCompare compares two files byte by byte without loading them into memory
func DeepCompareEq(file1, file2 string) bool {
	sf, err := os.Open(file1)
	if err != nil {
		log.Fatal(err)
	}

	df, err := os.Open(file2)
	if err != nil {
		log.Fatal(err)
	}

	sscan := bufio.NewScanner(sf)
	dscan := bufio.NewScanner(df)

	for sscan.Scan() {
		dscan.Scan()
		if !bytes.Equal(sscan.Bytes(), dscan.Bytes()) {
			return false
		}
	}
	return true
}
