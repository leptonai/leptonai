package metrics

import "testing"

func Test_deriveAPIPrefix(t *testing.T) {
	tt := []struct {
		fullPath    string
		expectedPfx string
		expectedN   int
	}{
		{
			fullPath:    "",
			expectedPfx: "/",
			expectedN:   0,
		},
		{
			fullPath:    "/",
			expectedPfx: "/",
			expectedN:   0,
		},
		{
			fullPath:    "//",
			expectedPfx: "/",
			expectedN:   0,
		},
		{
			fullPath:    "/a/",
			expectedPfx: "/a",
			expectedN:   1,
		},
		{
			fullPath:    "/a/b/",
			expectedPfx: "/a/b",
			expectedN:   2,
		},
		{
			fullPath:    "/a/b/c/",
			expectedPfx: "/a/b/c",
			expectedN:   3,
		},
		{
			fullPath:    "/a/b/c",
			expectedPfx: "/a/b/c",
			expectedN:   3,
		},
		{
			fullPath:    "/a/b/c/d",
			expectedPfx: "/a/b/c",
			expectedN:   3,
		},
		{
			fullPath:    "/a/b/c/d/e/f/g",
			expectedPfx: "/a/b/c",
			expectedN:   3,
		},
		{
			fullPath:    "/a/b/cd/e/f/g",
			expectedPfx: "/a/b/cd",
			expectedN:   3,
		},
		{
			fullPath:    "//a/b//cd//e/f/g",
			expectedPfx: "/a/b/cd",
			expectedN:   3,
		},
	}

	for i, v := range tt {
		if pfx, n := deriveAPIPrefix(v.fullPath); pfx != v.expectedPfx || n != v.expectedN {
			t.Errorf("test %d: expected %s and %d, got %s and %d", i, v.expectedPfx, v.expectedN, pfx, n)
		}
	}
}
