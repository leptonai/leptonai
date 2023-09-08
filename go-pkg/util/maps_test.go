package util

import (
	"fmt"
	"testing"
	"time"
)

func TestContainsStringsMap(t *testing.T) {
	superSet := make(map[string]string)
	subset := make(map[string]string)
	for i := 0; i < 100; i++ {
		k := fmt.Sprint(i)
		v := fmt.Sprint(time.Now().UnixNano())

		superSet[k] = v

		if i > 50 {
			subset[k] = v
		}
	}

	if !ContainsStringsMap(superSet, subset) {
		t.Fatal("expected superSet to contain subset")
	}
}
