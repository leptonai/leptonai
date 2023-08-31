//go:build !ignore_autogenerated
// +build !ignore_autogenerated

/*
Copyright 2023.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

// Code generated by controller-gen. DO NOT EDIT.

package v1alpha1

import (
	"k8s.io/apimachinery/pkg/runtime"
)

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Autoscaler) DeepCopyInto(out *Autoscaler) {
	*out = *in
	if in.ScaleDown != nil {
		in, out := &in.ScaleDown, &out.ScaleDown
		*out = new(ScaleDown)
		(*in).DeepCopyInto(*out)
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Autoscaler.
func (in *Autoscaler) DeepCopy() *Autoscaler {
	if in == nil {
		return nil
	}
	out := new(Autoscaler)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *EnvValue) DeepCopyInto(out *EnvValue) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new EnvValue.
func (in *EnvValue) DeepCopy() *EnvValue {
	if in == nil {
		return nil
	}
	out := new(EnvValue)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *EnvVar) DeepCopyInto(out *EnvVar) {
	*out = *in
	out.ValueFrom = in.ValueFrom
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new EnvVar.
func (in *EnvVar) DeepCopy() *EnvVar {
	if in == nil {
		return nil
	}
	out := new(EnvVar)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *LeptonDeployment) DeepCopyInto(out *LeptonDeployment) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ObjectMeta.DeepCopyInto(&out.ObjectMeta)
	in.Spec.DeepCopyInto(&out.Spec)
	out.Status = in.Status
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LeptonDeployment.
func (in *LeptonDeployment) DeepCopy() *LeptonDeployment {
	if in == nil {
		return nil
	}
	out := new(LeptonDeployment)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject is an autogenerated deepcopy function, copying the receiver, creating a new runtime.Object.
func (in *LeptonDeployment) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *LeptonDeploymentEndpoint) DeepCopyInto(out *LeptonDeploymentEndpoint) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LeptonDeploymentEndpoint.
func (in *LeptonDeploymentEndpoint) DeepCopy() *LeptonDeploymentEndpoint {
	if in == nil {
		return nil
	}
	out := new(LeptonDeploymentEndpoint)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *LeptonDeploymentList) DeepCopyInto(out *LeptonDeploymentList) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ListMeta.DeepCopyInto(&out.ListMeta)
	if in.Items != nil {
		in, out := &in.Items, &out.Items
		*out = make([]LeptonDeployment, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LeptonDeploymentList.
func (in *LeptonDeploymentList) DeepCopy() *LeptonDeploymentList {
	if in == nil {
		return nil
	}
	out := new(LeptonDeploymentList)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject is an autogenerated deepcopy function, copying the receiver, creating a new runtime.Object.
func (in *LeptonDeploymentList) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *LeptonDeploymentReplicaResourceRequirement) DeepCopyInto(out *LeptonDeploymentReplicaResourceRequirement) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LeptonDeploymentReplicaResourceRequirement.
func (in *LeptonDeploymentReplicaResourceRequirement) DeepCopy() *LeptonDeploymentReplicaResourceRequirement {
	if in == nil {
		return nil
	}
	out := new(LeptonDeploymentReplicaResourceRequirement)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *LeptonDeploymentResourceRequirement) DeepCopyInto(out *LeptonDeploymentResourceRequirement) {
	*out = *in
	out.LeptonDeploymentReplicaResourceRequirement = in.LeptonDeploymentReplicaResourceRequirement
	if in.MinReplicas != nil {
		in, out := &in.MinReplicas, &out.MinReplicas
		*out = new(int32)
		**out = **in
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LeptonDeploymentResourceRequirement.
func (in *LeptonDeploymentResourceRequirement) DeepCopy() *LeptonDeploymentResourceRequirement {
	if in == nil {
		return nil
	}
	out := new(LeptonDeploymentResourceRequirement)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *LeptonDeploymentSpec) DeepCopyInto(out *LeptonDeploymentSpec) {
	*out = *in
	out.LeptonDeploymentSystemSpec = in.LeptonDeploymentSystemSpec
	in.LeptonDeploymentUserSpec.DeepCopyInto(&out.LeptonDeploymentUserSpec)
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LeptonDeploymentSpec.
func (in *LeptonDeploymentSpec) DeepCopy() *LeptonDeploymentSpec {
	if in == nil {
		return nil
	}
	out := new(LeptonDeploymentSpec)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *LeptonDeploymentStatus) DeepCopyInto(out *LeptonDeploymentStatus) {
	*out = *in
	out.Endpoint = in.Endpoint
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LeptonDeploymentStatus.
func (in *LeptonDeploymentStatus) DeepCopy() *LeptonDeploymentStatus {
	if in == nil {
		return nil
	}
	out := new(LeptonDeploymentStatus)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *LeptonDeploymentSystemSpec) DeepCopyInto(out *LeptonDeploymentSystemSpec) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LeptonDeploymentSystemSpec.
func (in *LeptonDeploymentSystemSpec) DeepCopy() *LeptonDeploymentSystemSpec {
	if in == nil {
		return nil
	}
	out := new(LeptonDeploymentSystemSpec)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *LeptonDeploymentUserSpec) DeepCopyInto(out *LeptonDeploymentUserSpec) {
	*out = *in
	in.ResourceRequirement.DeepCopyInto(&out.ResourceRequirement)
	if in.Autoscaler != nil {
		in, out := &in.Autoscaler, &out.Autoscaler
		*out = new(Autoscaler)
		(*in).DeepCopyInto(*out)
	}
	if in.APITokens != nil {
		in, out := &in.APITokens, &out.APITokens
		*out = make([]TokenVar, len(*in))
		copy(*out, *in)
	}
	if in.Envs != nil {
		in, out := &in.Envs, &out.Envs
		*out = make([]EnvVar, len(*in))
		copy(*out, *in)
	}
	if in.Mounts != nil {
		in, out := &in.Mounts, &out.Mounts
		*out = make([]Mount, len(*in))
		copy(*out, *in)
	}
	if in.ImagePullSecrets != nil {
		in, out := &in.ImagePullSecrets, &out.ImagePullSecrets
		*out = make([]string, len(*in))
		copy(*out, *in)
	}
	if in.ResourceProvider != nil {
		in, out := &in.ResourceProvider, &out.ResourceProvider
		*out = new(string)
		**out = **in
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new LeptonDeploymentUserSpec.
func (in *LeptonDeploymentUserSpec) DeepCopy() *LeptonDeploymentUserSpec {
	if in == nil {
		return nil
	}
	out := new(LeptonDeploymentUserSpec)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Mount) DeepCopyInto(out *Mount) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Mount.
func (in *Mount) DeepCopy() *Mount {
	if in == nil {
		return nil
	}
	out := new(Mount)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *Photon) DeepCopyInto(out *Photon) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ObjectMeta.DeepCopyInto(&out.ObjectMeta)
	in.Spec.DeepCopyInto(&out.Spec)
	out.Status = in.Status
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new Photon.
func (in *Photon) DeepCopy() *Photon {
	if in == nil {
		return nil
	}
	out := new(Photon)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject is an autogenerated deepcopy function, copying the receiver, creating a new runtime.Object.
func (in *Photon) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *PhotonList) DeepCopyInto(out *PhotonList) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ListMeta.DeepCopyInto(&out.ListMeta)
	if in.Items != nil {
		in, out := &in.Items, &out.Items
		*out = make([]Photon, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new PhotonList.
func (in *PhotonList) DeepCopy() *PhotonList {
	if in == nil {
		return nil
	}
	out := new(PhotonList)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject is an autogenerated deepcopy function, copying the receiver, creating a new runtime.Object.
func (in *PhotonList) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *PhotonSpec) DeepCopyInto(out *PhotonSpec) {
	*out = *in
	if in.RequirementDependency != nil {
		in, out := &in.RequirementDependency, &out.RequirementDependency
		*out = make([]string, len(*in))
		copy(*out, *in)
	}
	if in.ExposedPorts != nil {
		in, out := &in.ExposedPorts, &out.ExposedPorts
		*out = make([]int32, len(*in))
		copy(*out, *in)
	}
	if in.ContainerArgs != nil {
		in, out := &in.ContainerArgs, &out.ContainerArgs
		*out = make([]string, len(*in))
		copy(*out, *in)
	}
	in.OpenAPISchema.DeepCopyInto(&out.OpenAPISchema)
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new PhotonSpec.
func (in *PhotonSpec) DeepCopy() *PhotonSpec {
	if in == nil {
		return nil
	}
	out := new(PhotonSpec)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *PhotonStatus) DeepCopyInto(out *PhotonStatus) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new PhotonStatus.
func (in *PhotonStatus) DeepCopy() *PhotonStatus {
	if in == nil {
		return nil
	}
	out := new(PhotonStatus)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *ResourceShape) DeepCopyInto(out *ResourceShape) {
	*out = *in
	out.Resource = in.Resource
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new ResourceShape.
func (in *ResourceShape) DeepCopy() *ResourceShape {
	if in == nil {
		return nil
	}
	out := new(ResourceShape)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *ScaleDown) DeepCopyInto(out *ScaleDown) {
	*out = *in
	if in.NoTrafficDurationInSeconds != nil {
		in, out := &in.NoTrafficDurationInSeconds, &out.NoTrafficDurationInSeconds
		*out = new(int32)
		**out = **in
	}
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new ScaleDown.
func (in *ScaleDown) DeepCopy() *ScaleDown {
	if in == nil {
		return nil
	}
	out := new(ScaleDown)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *TokenValue) DeepCopyInto(out *TokenValue) {
	*out = *in
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new TokenValue.
func (in *TokenValue) DeepCopy() *TokenValue {
	if in == nil {
		return nil
	}
	out := new(TokenValue)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto is an autogenerated deepcopy function, copying the receiver, writing into out. in must be non-nil.
func (in *TokenVar) DeepCopyInto(out *TokenVar) {
	*out = *in
	out.ValueFrom = in.ValueFrom
}

// DeepCopy is an autogenerated deepcopy function, copying the receiver, creating a new TokenVar.
func (in *TokenVar) DeepCopy() *TokenVar {
	if in == nil {
		return nil
	}
	out := new(TokenVar)
	in.DeepCopyInto(out)
	return out
}
