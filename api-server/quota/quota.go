package quota

import (
	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	"github.com/leptonai/lepton/go-pkg/deploymentutil"

	v1 "k8s.io/api/core/v1"
)

// Admit checks if a LeptonDeploymentResourceRequirement can be admitted to a ResourceQuota
// after release the resources used by the old deployment if any.
func Admit(q v1.ResourceQuota, r *leptonaiv1alpha1.LeptonDeploymentResourceRequirement, o *leptonaiv1alpha1.LeptonDeploymentResourceRequirement) bool {
	if o != nil { // release the resources used by the old deployment if any
		kc := deploymentutil.LeptonResourceToKubeResource(*o)
		for requestName, request := range kc.Requests {
			requestName = v1.ResourceName("requests." + requestName.String())
			_, ok := q.Spec.Hard[requestName]
			if !ok {
				// no limit set, continue
				continue
			}

			for i := 0; i < int(o.MinReplicas); i++ {
				// improve me: only release the resources actually conusmed by the old deployment
				// basically number of running pod...
				u := q.Status.Used[requestName]
				u.Sub(request)
				q.Status.Used[requestName] = u
			}
		}
	}

	kr := deploymentutil.LeptonResourceToKubeResource(*r)

	for requestName, request := range kr.Requests { // check if the new deployment can be admitted
		requestName = v1.ResourceName("requests." + requestName.String())

		h, ok := q.Spec.Hard[requestName]
		if !ok {
			// no limit set, continue
			continue
		}
		u := q.Status.Used[requestName]

		for i := 0; i < int(r.MinReplicas); i++ {
			u.Add(request)
		}

		if h.Cmp(u) < 0 {
			return false
		}
	}

	return true
}
