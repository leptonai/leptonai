package controller

import (
	"fmt"
	"path"

	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const (
	initContainerName     = "env-preparation"
	mainContainerName     = "main-container"
	photonVolumeName      = "photon"
	photonVolumeMountPath = "/photon"
	awscliImageURL        = "amazon/aws-cli"

	nvidiaGPUProductLabelKey = "nvidia.com/gpu.product"
	nvidiaGPUResourceKey     = "nvidia.com/gpu"

	labelKeyPhotonName           = "photon_name"
	labelKeyPhotonID             = "photon_id"
	labelKeyLeptonDeploymentName = "lepton_deployment_name"
	labelKeyLeptonDeploymentID   = "lepton_deployment_id"
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

func (k *deployment) createDeployment(or *metav1.OwnerReference) *appsv1.Deployment {
	ld := k.leptonDeployment
	podSpec := k.createDeploymentPodSpec()

	// Define the pod template
	template := corev1.PodTemplateSpec{
		ObjectMeta: metav1.ObjectMeta{
			Labels: map[string]string{
				labelKeyPhotonID:           ld.Spec.PhotonID,
				labelKeyLeptonDeploymentID: ld.GetSpecID(),
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
				labelKeyLeptonDeploymentID:   ld.GetSpecID(),
			},
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &ld.Spec.ResourceRequirement.MinReplicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					labelKeyLeptonDeploymentID: ld.GetSpecID(),
				},
			},
			Template: template,
		},
	}
	if or != nil {
		deployment.OwnerReferences = []metav1.OwnerReference{*or}
	}

	return deployment
}

func (k *deployment) photonDestPath() string {
	ld := k.leptonDeployment
	return photonVolumeMountPath + "/" + ld.GetUniqPhotonName()
}

func (k *deployment) newInitContainerCommand() []string {
	ld := k.leptonDeployment
	s3URL := fmt.Sprintf("s3://%s", path.Join(ld.Spec.BucketName, ld.Spec.PhotonPrefix, ld.GetUniqPhotonName()))
	// TODO support other clouds
	// aws s3 cp s3://my-bucket/example.txt ./example.txt
	return []string{"aws", "s3", "cp", s3URL, k.photonDestPath()}
}

func (k *deployment) newInitContainerArgs() []string {
	return []string{}
}

func (k *deployment) newInitContainer() corev1.Container {
	ld := k.leptonDeployment
	// Define the init container
	return corev1.Container{
		Name:    initContainerName,
		Image:   awscliImageURL,
		Command: k.newInitContainerCommand(),
		Args:    k.newInitContainerArgs(),
		Env:     util.ToContainerEnv(ld.Spec.Envs),
		VolumeMounts: []corev1.VolumeMount{
			{
				Name:      photonVolumeName,
				MountPath: photonVolumeMountPath,
			},
		},
	}
}

func (k *deployment) newMainContainerCommand() []string {
	return []string{"sh"}
}

func (k *deployment) newMainContainerArgs() []string {
	leptonCmd := fmt.Sprintf("lepton photon prepare -f %s; lepton photon run -f %[1]s", k.photonDestPath())
	return []string{"-c", leptonCmd}
}

func (k *deployment) gpuEnabled() bool {
	ld := k.leptonDeployment
	return ld.Spec.ResourceRequirement.AcceleratorType != "" && ld.Spec.ResourceRequirement.AcceleratorNum > 0
}

func (k *deployment) createDeploymentPodSpec() *corev1.PodSpec {
	ld := k.leptonDeployment
	env := util.ToContainerEnv(ld.Spec.Envs)

	// Define the shared volume
	sharedVolume := corev1.Volume{
		Name: photonVolumeName,
		VolumeSource: corev1.VolumeSource{
			EmptyDir: &corev1.EmptyDirVolumeSource{},
		},
	}

	cpu := resource.NewScaledQuantity(int64(ld.Spec.ResourceRequirement.CPU*1000), -3)
	// TODO: we may want to change memory to BinarySI
	memory := resource.NewQuantity(ld.Spec.ResourceRequirement.Memory*1024*1024, resource.BinarySI)
	// Define the main container
	resources := corev1.ResourceRequirements{
		Requests: corev1.ResourceList{
			corev1.ResourceCPU:    *cpu,
			corev1.ResourceMemory: *memory,
		},
		Limits: corev1.ResourceList{
			corev1.ResourceCPU:    *cpu,
			corev1.ResourceMemory: *memory,
		},
	}
	nodeSelector := map[string]string{}
	if k.gpuEnabled() {
		// if gpu is enabled, set gpu resource limit and node selector
		resources.Limits[corev1.ResourceName(k.gpuResourceKey)] = *resource.NewQuantity(int64(ld.Spec.ResourceRequirement.AcceleratorNum), resource.DecimalSI)
		nodeSelector[k.gpuProductLableKey] = ld.Spec.ResourceRequirement.AcceleratorType
	}

	container := corev1.Container{
		Name:            mainContainerName,
		Image:           ld.Spec.PhotonImage,
		ImagePullPolicy: corev1.PullAlways,
		Command:         k.newMainContainerCommand(),
		Args:            k.newMainContainerArgs(),
		Resources:       resources,
		Env:             env,

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
	}

	spec := &corev1.PodSpec{
		InitContainers:     []corev1.Container{k.newInitContainer()},
		Containers:         []corev1.Container{container},
		Volumes:            []corev1.Volume{sharedVolume},
		ServiceAccountName: ld.Spec.ServiceAccountName,
		NodeSelector:       nodeSelector,
	}

	return spec
}
