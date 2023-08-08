package util

import (
	"testing"
)

func TestRoundToTwoDecimalPlaces(t *testing.T) {
	tt := []struct {
		o    float64
		want float64
	}{
		{1.233, 1.23},
		{1.234, 1.23},
		{1.235, 1.24},
		{1.236, 1.24},
		{1.23388, 1.23},
		{1.23499, 1.23},
		{1.23599, 1.24},
		{1.23688, 1.24},
	}

	for _, tc := range tt {
		r := RoundToTwoDecimalPlaces(tc.o)
		if r != tc.want {
			t.Errorf("RoundToTwoDecimalPlaces(%f) = %f, want %f", tc.o, r, tc.want)
		}
	}
}
