package controller

import (
	"testing"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	"github.com/leptonai/lepton/go-pkg/k8s/leptonlabels"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/utils/ptr"
)

func TestCreateDeploymentPodSpecWithResourceProvider(t *testing.T) {
	d := &deployment{
		leptonDeployment: &leptonaiv1alpha1.LeptonDeployment{
			Spec: leptonaiv1alpha1.LeptonDeploymentSpec{
				LeptonDeploymentUserSpec: leptonaiv1alpha1.LeptonDeploymentUserSpec{
					ResourceAffinity: ptr.To[string](leptonlabels.LabelValueResourceProviderLambdaLabs),
				},
			},
		},
	}

	ps := d.createDeploymentPodSpec()

	if ps.HostNetwork == false {
		t.Errorf("HostNetwork should be true")
	}

	if ps.NodeSelector == nil {
		t.Errorf("NodeSelector should not be nil")
	} else {
		v := ps.NodeSelector[leptonlabels.LabelKeyLeptonResourceProvider]
		if v != leptonlabels.LabelValueResourceProviderLambdaLabs {
			t.Errorf("NodeSelector should be %s, got %s", leptonlabels.LabelValueResourceProviderLambdaLabs, v)
		}
	}

	if ps.Tolerations == nil {
		t.Errorf("Tolerations should not be nil")
	} else {
		if len(ps.Tolerations) != 1 {
			t.Errorf("Tolerations should have 1 element, got %d", len(ps.Tolerations))
		} else {
			toleration := ps.Tolerations[0]
			if toleration.Key != leptonlabels.LabelKeyLeptonResourceProvider {
				t.Errorf("Toleration.Key should be %s, got %s", leptonlabels.LabelKeyLeptonResourceProvider, toleration.Key)
			}
			if toleration.Value != leptonlabels.LabelValueResourceProviderLambdaLabs {
				t.Errorf("Toleration.Value should be %s, got %s", leptonlabels.LabelValueResourceProviderLambdaLabs, toleration.Value)
			}
			if toleration.Operator != corev1.TolerationOpEqual {
				t.Errorf("Toleration.Operator should be %s, got %s", corev1.TolerationOpEqual, toleration.Operator)
			}
			if toleration.Effect != corev1.TaintEffectNoSchedule {
				t.Errorf("Toleration.Effect should be %s, got %s", corev1.TaintEffectNoSchedule, toleration.Effect)
			}
		}
	}
}
