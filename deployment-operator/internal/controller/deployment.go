package controller

import (
	"fmt"
	"math"
	"path"

	"github.com/leptonai/lepton/api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	"github.com/leptonai/lepton/go-pkg/deploymentutil"
	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/k8s/secret"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/go-pkg/version"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/intstr"
)

const (
	initContainerName = "env-preparation"
	mainContainerName = "main-container"

	photonVolumeName      = "photon"
	photonVolumeMountPath = "/photon"
	awsVolumeName         = "aws"
	awsVolumeMountPath    = "/.aws"

	awscliImageURL = "amazon/aws-cli"

	nvidiaGPUProductLabelKey = "nvidia.com/gpu.product"
	nvidiaGPUResourceKey     = "nvidia.com/gpu"

	labelKeyPhotonName            = "photon_name"
	labelKeyPhotonID              = "photon_id"
	labelKeyLeptonDeploymentName  = "lepton_deployment_name"
	labelKeyLeptonDeploymentShape = "lepton_deployment_shape"

	readinessProbeInitialDelaySeconds = 5
	readinessProbePeriodSeconds       = 5
	readinessProbeFailureThreshold    = 12
	readinessProbeSuccessThreshold    = 1
	livenessProbeInitialDelaySeconds  = 600
	livenessProbePeriodSeconds        = 5
	livenessProbeFailureThreshold     = 12
	livenessProbeSuccessThreshold     = 1
)

type deployment struct {
	gpuResourceKey     string
	gpuProductLableKey string
	leptonDeployment   *leptonaiv1alpha1.LeptonDeployment
}

func newDeployment(ld *leptonaiv1alpha1.LeptonDeployment) *deployment {
	deployment := &deployment{
		leptonDeployment: ld,
	}
	return deployment
}

func newDeploymentNvidia(ld *leptonaiv1alpha1.LeptonDeployment) *deployment {
	deployment := newDeployment(ld)
	deployment.gpuProductLableKey = nvidiaGPUProductLabelKey
	deployment.gpuResourceKey = nvidiaGPUResourceKey
	return deployment
}

func (k *deployment) patchDeployment(d *appsv1.Deployment) {
	ld := k.leptonDeployment
	// TODO verify correctness
	spec := k.createDeploymentPodSpec()
	d.Spec.Template.Spec = *spec
	// We have to handle the number of replicas separately because it is not
	// in the pod spec. We are not able to update the whole deployment spec
	// because other fields like labelSelector is immutable.
	d.Spec.Replicas = &ld.Spec.ResourceRequirement.MinReplicas
}

func (k *deployment) createDeployment(or []metav1.OwnerReference) *appsv1.Deployment {
	ld := k.leptonDeployment
	podSpec := k.createDeploymentPodSpec()

	// Define the pod template
	template := corev1.PodTemplateSpec{
		ObjectMeta: metav1.ObjectMeta{
			Labels: map[string]string{
				labelKeyPhotonID:              ld.Spec.PhotonID,
				labelKeyLeptonDeploymentName:  ld.GetSpecName(),
				labelKeyLeptonDeploymentShape: ld.GetShape(),
			},
		},
		Spec: *podSpec,
	}

	// Define the deployment
	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      ld.GetSpecName(),
			Namespace: ld.Namespace,
			Labels: map[string]string{
				labelKeyPhotonName:           ld.Spec.PhotonName,
				labelKeyPhotonID:             ld.Spec.PhotonID,
				labelKeyLeptonDeploymentName: ld.GetSpecName(),
			},
			OwnerReferences: or,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &ld.Spec.ResourceRequirement.MinReplicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					labelKeyLeptonDeploymentName: ld.GetSpecName(),
				},
			},
			Template: template,
		},
	}

	return deployment
}

func (k *deployment) photonDestPath() string {
	ld := k.leptonDeployment
	return photonVolumeMountPath + "/" + ld.Spec.PhotonID
}

func (k *deployment) newInitContainerCommand() []string {
	ld := k.leptonDeployment
	s3URL := fmt.Sprintf("s3://%s", path.Join(ld.Spec.BucketName, ld.Spec.PhotonPrefix, ld.Spec.PhotonID))
	// TODO support other clouds
	// aws s3 cp s3://my-bucket/example.txt ./example.txt
	return []string{"aws", "s3", "cp", s3URL, k.photonDestPath()}
}

func (k *deployment) newInitContainerArgs() []string {
	return []string{}
}

func (k *deployment) newInitContainer() corev1.Container {
	s3ReadOnlyAccessK8sSecretName := k.leptonDeployment.Spec.S3ReadOnlyAccessK8sSecretName
	// set a default value for backward compatibility
	if s3ReadOnlyAccessK8sSecretName == "" {
		s3ReadOnlyAccessK8sSecretName = "s3-ro-key"
	}
	return corev1.Container{
		Name:  initContainerName,
		Image: awscliImageURL,
		Env: []corev1.EnvVar{
			{
				Name:  "HOME",
				Value: "/",
			},
			{
				Name: "AWS_ACCESS_KEY_ID",
				ValueFrom: &corev1.EnvVarSource{
					SecretKeyRef: &corev1.SecretKeySelector{
						LocalObjectReference: corev1.LocalObjectReference{
							Name: s3ReadOnlyAccessK8sSecretName,
						},
						Key: "AWS_ACCESS_KEY_ID",
					},
				},
			},
			{
				Name: "AWS_SECRET_ACCESS_KEY",
				ValueFrom: &corev1.EnvVarSource{
					SecretKeyRef: &corev1.SecretKeySelector{
						LocalObjectReference: corev1.LocalObjectReference{
							Name: s3ReadOnlyAccessK8sSecretName,
						},
						Key: "AWS_SECRET_ACCESS_KEY",
					},
				},
			},
		},
		Resources: deploymentutil.LeptonResourceToKubeResource(k.leptonDeployment.Spec.ResourceRequirement),
		Command:   k.newInitContainerCommand(),
		Args:      k.newInitContainerArgs(),
		VolumeMounts: []corev1.VolumeMount{
			{
				Name:      photonVolumeName,
				MountPath: photonVolumeMountPath,
			},
			{
				Name:      awsVolumeName,
				MountPath: awsVolumeMountPath,
			},
		},
		SecurityContext: k8s.DefaultContainerSecurityContext(),
	}
}

func (k *deployment) newMainContainerCommand() []string {
	return []string{"sh"}
}

func (k *deployment) newMainContainerArgs() []string {
	lepInstallCmd := fmt.Sprintf("if ! command -v lep; then pip install https://lepton-sdk.s3.amazonaws.com/release/leptonai-%s-py3-none-any.whl; fi", version.Release)
	leptonCmd := fmt.Sprintf("lep photon prepare -f %s; lep photon run -f %[1]s", k.photonDestPath())
	return []string{"-c", lepInstallCmd + "; " + leptonCmd}
}

func (k *deployment) gpuEnabled() bool {
	ld := k.leptonDeployment
	an, at := ld.Spec.ResourceRequirement.GetAcceleratorRequirement()

	return at != "" && an > 0
}

// TODO: test me!
func (k *deployment) createDeploymentPodSpec() *corev1.PodSpec {
	ld := k.leptonDeployment

	resources := deploymentutil.LeptonResourceToKubeResource(ld.Spec.ResourceRequirement)
	// We do not want non-GPU workloads to waste our GPU resources.
	// Use taint to not schedule those on GPU.
	// All pods without matching tolerations to these taints won't be scheduled.
	//
	// Assumption.
	// GPU nodes must be tainted with the matching value.
	//
	// ref. https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/
	// ref. https://docs.aws.amazon.com/eks/latest/userguide/node-taints-managed-node-groups.html
	// ref. https://www.eksworkshop.com/docs/fundamentals/managed-node-groups/taints/implementing-tolerations
	//
	// NOTE: gpu operator automatically adds tolerations to GPU pods
	// we just need GPU node taints
	// ref. https://github.com/leptonai/lepton/issues/1220
	// tolerations := []corev1.Toleration{}
	nodeSelector := map[string]string{}
	if k.gpuEnabled() {
		_, acctype := ld.Spec.ResourceRequirement.GetAcceleratorRequirement()
		// only schedule the pod with exact matching node labels
		nodeSelector[k.gpuProductLableKey] = acctype
	}

	envs := util.ToContainerEnv(ld.Spec.Envs)
	// Add lepton runtime envs to the container envs
	runtimeEnvs := []corev1.EnvVar{
		{Name: "LEPTON_WORKSPACE_NAME", Value: ld.Spec.WorkspaceName},
		{Name: "LEPTON_PHOTON_NAME", Value: ld.Spec.PhotonName},
		{Name: "LEPTON_PHOTON_ID", Value: ld.Spec.PhotonID},
		{Name: "LEPTON_DEPLOYMENT_NAME", Value: ld.Spec.Name},
		{Name: "LEPTON_RESOURCE_ACCELERATOR_TYPE", Value: nodeSelector[k.gpuProductLableKey]},
	}
	envs = append(envs, runtimeEnvs...)

	// Set the expected number of threads for OMP and MKL to avoid CPU cache thrashing.
	// Do not overwrite user's setting.
	threads := fmt.Sprint(math.Ceil(resources.Limits.Cpu().AsApproximateFloat64()))
	setOT, setMT := false, false
	for _, e := range envs {
		if e.Name == "OMP_NUM_THREADS" {
			setOT = true
		}
		if e.Name == "MKL_NUM_THREADS" {
			setMT = true
		}
	}
	if !setOT {
		envs = append(envs, corev1.EnvVar{Name: "OMP_NUM_THREADS", Value: threads})
	}
	if !setMT {
		envs = append(envs, corev1.EnvVar{Name: "MKL_NUM_THREADS", Value: threads})
	}

	container := corev1.Container{
		Name:            mainContainerName,
		Image:           ld.Spec.PhotonImage,
		ImagePullPolicy: corev1.PullAlways,
		Command:         k.newMainContainerCommand(),
		Args:            k.newMainContainerArgs(),
		Resources:       resources,
		Env:             envs,

		Ports: []corev1.ContainerPort{
			{
				Name:          "http",
				ContainerPort: service.Port,
			},
		},
		VolumeMounts: []corev1.VolumeMount{
			{
				Name:      photonVolumeName,
				MountPath: photonVolumeMountPath,
			},
		},
		SecurityContext: k8s.RootContainerSecurityContext(),
		ReadinessProbe: &corev1.Probe{
			ProbeHandler: corev1.ProbeHandler{
				TCPSocket: &corev1.TCPSocketAction{
					Port: intstr.FromInt(service.Port),
				},
			},
			InitialDelaySeconds: readinessProbeInitialDelaySeconds,
			PeriodSeconds:       readinessProbePeriodSeconds,
			FailureThreshold:    readinessProbeFailureThreshold,
			SuccessThreshold:    readinessProbeSuccessThreshold,
		},
		LivenessProbe: &corev1.Probe{
			ProbeHandler: corev1.ProbeHandler{
				TCPSocket: &corev1.TCPSocketAction{
					Port: intstr.FromInt(service.Port),
				},
			},
			InitialDelaySeconds: livenessProbeInitialDelaySeconds,
			PeriodSeconds:       livenessProbePeriodSeconds,
			FailureThreshold:    livenessProbeFailureThreshold,
			SuccessThreshold:    livenessProbeSuccessThreshold,
		},
	}

	volumes := []corev1.Volume{}
	for i, m := range k.leptonDeployment.Spec.Mounts {
		ns, name := k.leptonDeployment.Namespace, k.leptonDeployment.GetSpecName()
		// TODO: ensure the name is short enough
		pvname := getPVName(ns, name, i)
		pvcname := getPVCName(ns, name, i)

		container.VolumeMounts = append(container.VolumeMounts, corev1.VolumeMount{
			Name:      pvname,
			MountPath: m.MountPath,
		})

		pvVolume := corev1.Volume{
			Name: pvname,
			VolumeSource: corev1.VolumeSource{
				PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
					ClaimName: pvcname,
				},
			},
		}
		volumes = append(volumes, pvVolume)
	}

	// Define the shared volume
	sharedVolume := corev1.Volume{
		Name: photonVolumeName,
		VolumeSource: corev1.VolumeSource{
			EmptyDir: &corev1.EmptyDirVolumeSource{},
		},
	}

	awsVolume := corev1.Volume{
		Name: awsVolumeName,
		VolumeSource: corev1.VolumeSource{
			EmptyDir: &corev1.EmptyDirVolumeSource{},
		},
	}

	enableServiceLinks := false
	autoMountServiceAccountToken := false
	spec := &corev1.PodSpec{
		InitContainers: []corev1.Container{k.newInitContainer()},
		Containers:     []corev1.Container{container},
		Volumes:        append(volumes, sharedVolume, awsVolume),
		NodeSelector:   nodeSelector,
		// https://aws.github.io/aws-eks-best-practices/security/docs/pods/#disable-service-discovery
		EnableServiceLinks: &enableServiceLinks,
		// https://aws.github.io/aws-eks-best-practices/security/docs/pods/#disable-automountserviceaccounttoken
		AutomountServiceAccountToken: &autoMountServiceAccountToken,
		SecurityContext:              k8s.DefaultPodSecurityContext(),
	}

	for _, sn := range ld.Spec.ImagePullSecrets {
		spec.ImagePullSecrets = append(spec.ImagePullSecrets, corev1.LocalObjectReference{Name: secret.ImagePullSecretPrefix + sn})
	}

	return spec
}
