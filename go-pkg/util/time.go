package util

import "time"

func RoundTimeByHour(t time.Time) time.Time {
	return t.Round(time.Hour)
}
