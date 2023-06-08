package git

import (
	"os"
	"testing"
)

func TestClone(t *testing.T) {
	repoURL := "https://github.com/leptonai/lepton.git"

	dir, err := os.MkdirTemp("", "clone-test")
	if err != nil {
		t.Fatalf("failed to create a tmp dir: %s\n", err)
	}
	defer os.RemoveAll(dir)

	err = Clone(dir, repoURL)
	if err != nil {
		t.Fatal(err)
	}
}
