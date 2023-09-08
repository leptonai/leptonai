package k8s

import (
	"errors"
	"testing"
)

func TestIsPodInitializingError(t *testing.T) {
	tt := []struct {
		err  error
		want bool
	}{
		{
			err:  nil,
			want: false,
		},
		{
			err:  errors.New("some random error"),
			want: false,
		},
		{
			err:  errors.New("\"main-container\" in pod \"tuna-stable-fbro-all-89887d9d7-qvs26\" is waiting to start: PodInitializing"),
			want: true,
		},
	}

	for _, tc := range tt {
		got := IsPodInitializingError(tc.err)
		if got != tc.want {
			t.Errorf("IsPodInitializingError(%v) = %v, want %v", tc.err, got, tc.want)
		}
	}
}
