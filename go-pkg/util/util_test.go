package util

import "testing"

func TestRandString(t *testing.T) {
	result := RandString(10)
	if len(result) != 10 {
		t.Errorf("RandString(10) = %s; want length 10", result)
	}
}

func TestContainsString(t *testing.T) {
	slice := []string{"a", "b", "c"}
	if !ContainsString(slice, "a") {
		t.Errorf("ContainsString(slice, \"a\") = false; want true")
	}
	if ContainsString(slice, "d") {
		t.Errorf("ContainsString(slice, \"d\") = true; want false")
	}
}

func TestRemoveString(t *testing.T) {
	slice := []string{"a", "b", "c"}
	result := RemoveString(slice, "a")
	if ContainsString(result, "a") {
		t.Errorf("RemoveString(slice, \"a\") = %v; want not contain \"a\"", result)
	}
	if len(result) != 2 {
		t.Errorf("RemoveString(slice, \"a\") = %v; want length 2", result)
	}
}
