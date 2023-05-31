package e2etests

import (
	"testing"

	"github.com/leptonai/lepton/lepton-api-server/util"
)

func TestDeploymentCreate(t *testing.T) {
	util.MustInitK8sClientSet()
}
