package util

import "math"

// RoundToTwoDecimalPlaces rounds a float64 to two decimal places
func RoundToTwoDecimalPlaces(f float64) float64 {
	return float64(math.Round(f*100)) / 100
}
