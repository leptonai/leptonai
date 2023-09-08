package util

import (
	"testing"
	"time"
)

func TestRoundTimeByHour(t *testing.T) {
	tt := []struct {
		input    time.Time
		expected time.Time
	}{
		{
			input:    time.Date(2023, time.August, 1, 15, 30, 0, 0, time.UTC),
			expected: time.Date(2023, time.August, 1, 16, 0, 0, 0, time.UTC),
		},
		{
			input:    time.Date(2023, time.August, 1, 14, 59, 0, 0, time.UTC),
			expected: time.Date(2023, time.August, 1, 15, 0, 0, 0, time.UTC),
		},
		{
			input:    time.Date(2023, time.August, 1, 14, 59, 0, 0, time.UTC),
			expected: time.Date(2023, time.August, 1, 15, 0, 0, 0, time.UTC),
		},
		{
			input:    time.Date(2023, time.August, 1, 15, 12, 0, 0, time.UTC),
			expected: time.Date(2023, time.August, 1, 15, 0, 0, 0, time.UTC),
		},
		{
			input:    time.Date(2023, time.December, 31, 23, 59, 0, 0, time.UTC),
			expected: time.Date(2024, time.January, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			input:    time.Date(2023, time.December, 31, 23, 29, 0, 0, time.UTC),
			expected: time.Date(2023, time.December, 31, 23, 0, 0, 0, time.UTC),
		},
		{
			input:    time.Date(2023, time.December, 31, 23, 30, 0, 0, time.UTC),
			expected: time.Date(2024, time.January, 1, 0, 0, 0, 0, time.UTC),
		},
		{
			input:    time.Date(2023, time.December, 31, 23, 31, 0, 0, time.UTC),
			expected: time.Date(2024, time.January, 1, 0, 0, 0, 0, time.UTC),
		},
	}
	for i, tv := range tt {
		rounded := RoundTimeByHour(tv.input)
		if rounded != tv.expected {
			t.Errorf("#%d: expected %v, got %v", i, tv.expected, rounded)
		}
	}
}
