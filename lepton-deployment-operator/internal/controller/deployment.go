package controller

import (
	"fmt"
	"log"
	"path"

	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
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

	labelKeyPhotonName           = "photon_name"
	labelKeyPhotonID             = "photon_id"
	labelKeyLeptonDeploymentName = "lepton_deployment_name"
	labelKeyLeptonDeploymentID   = "lepton_deployment_id"

	readinessProbeInitialDelaySeconds = 5
	readinessProbePeriodSeconds       = 5
	livenessProbeInitialDelaySeconds  = 15
	livenessProbePeriodSeconds        = 20
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
			OwnerReferences: or,
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
	return corev1.Container{
		Name:  initContainerName,
		Image: awscliImageURL,
		Env: []corev1.EnvVar{
			{
				Name:  "HOME",
				Value: "/",
			},
		},
		Command: k.newInitContainerCommand(),
		Args:    k.newInitContainerArgs(),
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
	leptonCmd := fmt.Sprintf("lep photon prepare -f %s; lep photon run -f %[1]s", k.photonDestPath())
	return []string{"-c", leptonCmd}
}

func (k *deployment) gpuEnabled() bool {
	ld := k.leptonDeployment
	return ld.Spec.ResourceRequirement.AcceleratorType != "" && ld.Spec.ResourceRequirement.AcceleratorNum > 0
}

func (k *deployment) createDeploymentPodSpec() *corev1.PodSpec {
	ld := k.leptonDeployment
	env := util.ToContainerEnv(ld.Spec.Envs)

	cpu := resource.NewScaledQuantity(int64(ld.Spec.ResourceRequirement.CPU*1000), -3)
	memory := resource.NewQuantity(ld.Spec.ResourceRequirement.Memory*1024*1024, resource.BinarySI)
	storage := resource.NewQuantity(ld.Spec.ResourceRequirement.EphemeralStorageInGB*1024*1024*1024, resource.BinarySI)

	if ld.Spec.ResourceRequirement.ResourceShape != "" {
		replicaResourceRequirement, err := shapeToReplicaResourceRequirement(ld.Spec.ResourceRequirement.ResourceShape)
		if err != nil {
			log.Fatalf("Unexpected shape to requirement error %v", err)
		}

		cpu = resource.NewScaledQuantity(int64(replicaResourceRequirement.CPU*1000), -3)
		memory = resource.NewQuantity(replicaResourceRequirement.Memory*1024*1024, resource.BinarySI)
		storage = resource.NewQuantity(replicaResourceRequirement.EphemeralStorageInGB*1024*1024*1024, resource.BinarySI)
	}

	// Define the main container
	resources := corev1.ResourceRequirements{
		Requests: corev1.ResourceList{
			corev1.ResourceCPU:              *cpu,
			corev1.ResourceMemory:           *memory,
			corev1.ResourceEphemeralStorage: *storage,
		},
		Limits: corev1.ResourceList{
			corev1.ResourceCPU:              *cpu,
			corev1.ResourceMemory:           *memory,
			corev1.ResourceEphemeralStorage: *storage,
		},
	}
	nodeSelector := map[string]string{}
	if k.gpuEnabled() {
		// if gpu is enabled, set gpu resource limit and node selector
		rv := *resource.NewQuantity(int64(ld.Spec.ResourceRequirement.AcceleratorNum), resource.DecimalSI)
		resources.Limits[corev1.ResourceName(k.gpuResourceKey)] = rv

		// cluster-autoscaler uses this key to prevent early scale-down on new/upcoming pods
		// even without this, execution uses the "resources.Limits" as defaults
		resources.Requests[corev1.ResourceName(k.gpuResourceKey)] = rv

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
		SecurityContext: k8s.RootContainerSecurityContext(),
		ReadinessProbe: &corev1.Probe{
			ProbeHandler: corev1.ProbeHandler{
				TCPSocket: &corev1.TCPSocketAction{
					Port: intstr.FromInt(service.Port),
				},
			},
			InitialDelaySeconds: readinessProbeInitialDelaySeconds,
			PeriodSeconds:       readinessProbePeriodSeconds,
		},
		LivenessProbe: &corev1.Probe{
			ProbeHandler: corev1.ProbeHandler{
				TCPSocket: &corev1.TCPSocketAction{
					Port: intstr.FromInt(service.Port),
				},
			},
			InitialDelaySeconds: livenessProbeInitialDelaySeconds,
			PeriodSeconds:       livenessProbePeriodSeconds,
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
		InitContainers:     []corev1.Container{k.newInitContainer()},
		Containers:         []corev1.Container{container},
		Volumes:            append(volumes, sharedVolume, awsVolume),
		ServiceAccountName: ld.Spec.ServiceAccountName,
		NodeSelector:       nodeSelector,
		// https://aws.github.io/aws-eks-best-practices/security/docs/pods/#disable-service-discovery
		EnableServiceLinks: &enableServiceLinks,
		// https://aws.github.io/aws-eks-best-practices/security/docs/pods/#disable-automountserviceaccounttoken
		AutomountServiceAccountToken: &autoMountServiceAccountToken,
		SecurityContext:              k8s.DefaultPodSecurityContext(),
	}

	return spec
}

func shapeToReplicaResourceRequirement(shape leptonaiv1alpha1.LeptonDeploymentResourceShape) (*leptonaiv1alpha1.LeptonDeploymentReplicaResourceRequirement, error) {
	s := leptonaiv1alpha1.SupportedShapesAWS[shape]
	if s == nil {
		return nil, fmt.Errorf("shape %s is not supported", shape)
	}

	return &s.Resource, nil
}
