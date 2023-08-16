package exitcode

import "testing"

func TestCodeToError(t *testing.T) {
	tt := []struct {
		code     int32
		expected string
	}{
		{0, "Success"},
		{1, "General application errors: such as divide by zero and other impermissible operations"},
		{133, "Fatal error signal 5: Terminated by signal 5"},
		{256, "Unknown error with exit code 256"},
	}

	for _, tc := range tt {
		if CodeToError(tc.code) != tc.expected {
			t.Errorf("CodeToError(%d) expected %s, got %s", tc.code, tc.expected, CodeToError(tc.code))
		}
	}
}
