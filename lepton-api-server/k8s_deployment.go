package main

import (
	"context"
	"fmt"

	"github.com/leptonai/lepton/lepton-api-server/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var (
	awscliImageURL      = "amazon/aws-cli"
	deploymentNamespace = "default"
)

const (
	nvidiaGPUResourceName    = "nvidia.com/gpu"
	nvidiaGPUProductLabelKey = "nvidia.com/gpu.product"

	mainContainerName = "main-container"

	photonVolumeName      = "photon"
	photonVolumeMountPath = "/photon"
)

func patchDeployment(ld *leptonaiv1alpha1.LeptonDeployment) error {
	ph := photonDB.GetByID(ld.Spec.PhotonID)
	if ph == nil {
		return fmt.Errorf("photon %s does not exist", ld.Spec.PhotonID)
	}

	clientset := util.MustInitK8sClientSet()

	deployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Get(context.TODO(), ld.GetName(), metav1.GetOptions{})
	if err != nil {
		return err
	}

	spec, err := createDeploymentPodSpec(ld)
	if err != nil {
		return err
	}
	deployment.Spec.Template.Spec = *spec
	// We have to handle the number of replicas separately because it is not
	// in the pod spec. We are not able to update the whole deployment spec
	// because other fields like labelSelector is immutable.
	deployment.Spec.Replicas = int32Ptr(int32(ld.Spec.ResourceRequirement.MinReplicas))

	// Patch the deployment
	_, err = clientset.AppsV1().Deployments(deploymentNamespace).
		Update(context.TODO(), deployment, metav1.UpdateOptions{})
	if err != nil {
		return err
	}

	return nil
}

func createDeployment(ld *leptonaiv1alpha1.LeptonDeployment, or metav1.OwnerReference) error {
	ph := photonDB.GetByID(ld.Spec.PhotonID)
	if ph == nil {
		return fmt.Errorf("photon %s does not exist", ld.Spec.PhotonID)
	}

	podSpec, err := createDeploymentPodSpec(ld)
	if err != nil {
		return err
	}

	// Define the pod template
	template := corev1.PodTemplateSpec{
		ObjectMeta: metav1.ObjectMeta{
			Labels: map[string]string{
				"photon":          ph.GetUniqName(),
				"deployment_name": ld.GetName(),
				"deployment_id":   ld.GetID(),
			},
		},
		Spec: *podSpec,
	}

	// Define the deployment
	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:            ld.GetName(),
			Namespace:       deploymentNamespace,
			OwnerReferences: []metav1.OwnerReference{or},
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: int32Ptr(int32(ld.Spec.ResourceRequirement.MinReplicas)),
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"deployment_id": ld.GetID(),
				},
			},
			Template: template,
		},
	}

	clientset := util.MustInitK8sClientSet()
	createdDeployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Create(context.Background(), deployment, metav1.CreateOptions{})
	if err != nil {
		return err
	}

	fmt.Printf("Created deployment %q.\n", createdDeployment.GetObjectMeta().GetName())

	return nil
}

func int32Ptr(i int32) *int32 { return &i }

func deploymentState(lds ...*leptonaiv1alpha1.LeptonDeployment) []leptonaiv1alpha1.LeptonDeploymentState {
	clientset := util.MustInitK8sClientSet()

	states := make([]leptonaiv1alpha1.LeptonDeploymentState, 0, len(lds))
	for _, ld := range lds {
		// Get the deployment
		deployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Get(context.TODO(), ld.GetName(), metav1.GetOptions{})
		if err != nil {
			states = append(states, leptonaiv1alpha1.LeptonDeploymentStateUnknown)
			continue
		}

		// Get the deployment status
		status := deployment.Status
		if status.Replicas == status.ReadyReplicas {
			states = append(states, leptonaiv1alpha1.LeptonDeploymentStateRunning)
		} else {
			states = append(states, leptonaiv1alpha1.LeptonDeploymentStateNotReady)
		}
	}

	return states
}

func photonDestPath(ph *leptonaiv1alpha1.Photon) string {
	return photonVolumeMountPath + "/" + ph.GetUniqName()
}

func newInitContainerCommand(ph *leptonaiv1alpha1.Photon) []string {
	// use path.join?
	s3URL := fmt.Sprintf("s3://%s/%s/%s", *bucketNameFlag, *photonPrefixFlag, ph.GetUniqName())
	// TODO support other clouds
	// aws s3 cp s3://my-bucket/example.txt ./example.txt
	return []string{"aws", "s3", "cp", s3URL, photonDestPath(ph)}
}

func newInitContainerArgs(ph *leptonaiv1alpha1.Photon) []string {
	return []string{}
}

func newInitContainer(ph *leptonaiv1alpha1.Photon, env []corev1.EnvVar) corev1.Container {
	// Define the init container
	return corev1.Container{
		Name:    "env-preparation",
		Image:   awscliImageURL,
		Command: newInitContainerCommand(ph),
		Args:    newInitContainerArgs(ph),
		Env:     env,
		VolumeMounts: []corev1.VolumeMount{
			{
				Name:      photonVolumeName,
				MountPath: photonVolumeMountPath,
			},
		},
	}
}

func newMainContainerCommand(ph *leptonaiv1alpha1.Photon) []string {
	return []string{"sh"}
}

func newMainContainerArgs(ph *leptonaiv1alpha1.Photon) []string {
	leptonCmd := fmt.Sprintf("lepton photon prepare -f %s; lepton photon run -f %[1]s", photonDestPath(ph))
	return []string{"-c", leptonCmd}
}

func createDeploymentPodSpec(ld *leptonaiv1alpha1.LeptonDeployment) (*corev1.PodSpec, error) {
	ph := photonDB.GetByID(ld.Spec.PhotonID)
	if ph == nil {
		return nil, fmt.Errorf("photon %s does not exist", ld.Spec.PhotonID)
	}
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
	memory := resource.NewScaledQuantity(ld.Spec.ResourceRequirement.Memory, 6)
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
	if ld.Spec.ResourceRequirement.AcceleratorType != "" && ld.Spec.ResourceRequirement.AcceleratorNum > 0 {
		// if gpu is enabled, set gpu resource limit and node selector
		resources.Limits[nvidiaGPUResourceName] = *resource.NewQuantity(int64(ld.Spec.ResourceRequirement.AcceleratorNum), resource.DecimalSI)
		nodeSelector[nvidiaGPUProductLabelKey] = ld.Spec.ResourceRequirement.AcceleratorType
	}

	container := corev1.Container{
		Name:            mainContainerName,
		Image:           ph.Spec.Image,
		ImagePullPolicy: corev1.PullAlways,
		Command:         newMainContainerCommand(ph),
		Args:            newMainContainerArgs(ph),
		Resources:       resources,
		Env:             env,

		Ports: []corev1.ContainerPort{
			{
				Name:          "http",
				ContainerPort: 8080,
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
		InitContainers:     []corev1.Container{newInitContainer(ph, env)},
		Containers:         []corev1.Container{container},
		Volumes:            []corev1.Volume{sharedVolume},
		ServiceAccountName: *serviceAccountNameFlag,
		NodeSelector:       nodeSelector,
	}

	return spec, nil
}
