package util

import "testing"

func TestUpdateDefaultRegistry(t *testing.T) {
	tests := []struct {
		image         string
		expectedImage string
	}{
		{
			image:         "default/lepton:latest",
			expectedImage: "test.com/lepton:latest",
		},
		{
			image:         "605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:latest",
			expectedImage: "test.com/lepton:latest",
		},
		{
			image:         "private.com/lepton:latest",
			expectedImage: "private.com/lepton:latest",
		},
	}

	for _, tt := range tests {
		actualImage := UpdateDefaultRegistry(tt.image, "test.com")
		if actualImage != tt.expectedImage {
			t.Errorf("expected %s, got %s", tt.expectedImage, actualImage)
		}
	}
}
