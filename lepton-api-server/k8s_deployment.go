package main

import (
	"context"
	"fmt"

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

func patchDeployment(ld *LeptonDeployment) error {
	photonMapRWLock.RLock()
	ph := photonById[ld.PhotonID]
	photonMapRWLock.RUnlock()
	if ph == nil {
		return fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}

	// Create a Kubernetes client
	clientset := mustInitK8sClientSet()

	deployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Get(context.TODO(), ld.Name, metav1.GetOptions{})
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
	deployment.Spec.Replicas = int32Ptr(int32(ld.ResourceRequirement.MinReplicas))

	// Patch the deployment
	_, err = clientset.AppsV1().Deployments(deploymentNamespace).Update(context.TODO(), deployment, metav1.UpdateOptions{})
	if err != nil {
		return err
	}

	return nil
}

func createDeployment(ld *LeptonDeployment, or metav1.OwnerReference) error {
	photonMapRWLock.RLock()
	ph := photonById[ld.PhotonID]
	photonMapRWLock.RUnlock()
	if ph == nil {
		return fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}

	podSpec, err := createDeploymentPodSpec(ld)
	if err != nil {
		return err
	}

	// Define the pod template
	template := corev1.PodTemplateSpec{
		ObjectMeta: metav1.ObjectMeta{
			Labels: map[string]string{
				"photon":          joinNameByDash(ph.Name, ph.ID),
				"deployment_name": ld.Name,
				"deployment_id":   ld.ID,
			},
		},
		Spec: *podSpec,
	}

	// Define the deployment
	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:            ld.Name,
			Namespace:       deploymentNamespace,
			OwnerReferences: []metav1.OwnerReference{or},
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: int32Ptr(int32(ld.ResourceRequirement.MinReplicas)),
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"deployment_id": ld.ID,
				},
			},
			Template: template,
		},
	}

	// Create the deployment
	clientset := mustInitK8sClientSet()
	createdDeployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Create(context.Background(), deployment, metav1.CreateOptions{})
	if err != nil {
		return err
	}

	fmt.Printf("Created deployment %q.\n", createdDeployment.GetObjectMeta().GetName())

	return nil
}

func int32Ptr(i int32) *int32 { return &i }

type DeploymentState string

const (
	DeploymentStateRunning  DeploymentState = "Running"
	DeploymentStateNotReady DeploymentState = "Not Ready"
	DeploymentStateStarting DeploymentState = "Starting"
	DeploymentStateUpdating DeploymentState = "Updating"
	DeploymentStateUnknown  DeploymentState = "Unknown"
)

func deploymentState(lds ...*LeptonDeployment) []DeploymentState {
	// Create a Kubernetes client
	clientset := mustInitK8sClientSet()

	states := make([]DeploymentState, 0, len(lds))
	for _, ld := range lds {
		// Get the deployment
		deployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Get(context.TODO(), ld.Name, metav1.GetOptions{})
		if err != nil {
			states = append(states, DeploymentStateUnknown)
			continue
		}

		// Get the deployment status
		status := deployment.Status
		if status.Replicas == status.ReadyReplicas {
			states = append(states, DeploymentStateRunning)
		} else {
			states = append(states, DeploymentStateNotReady)
		}
	}

	return states
}

func photonDestPath(ph *Photon) string {
	return photonVolumeMountPath + "/" + joinNameByDash(ph.Name, ph.ID)
}

func newInitContainerCommand(ph *Photon) []string {
	// use path.join?
	s3URL := fmt.Sprintf("s3://%s/%s/%s", *bucketNameFlag, *photonPrefixFlag, joinNameByDash(ph.Name, ph.ID))
	// TODO support other clouds
	// aws s3 cp s3://my-bucket/example.txt ./example.txt
	return []string{"aws", "s3", "cp", s3URL, photonDestPath(ph)}
}

func newInitContainerArgs(ph *Photon) []string {
	return []string{}
}

func newInitContainer(ph *Photon) corev1.Container {
	// Define the init container
	return corev1.Container{
		Name:    "env-preparation",
		Image:   awscliImageURL,
		Command: newInitContainerCommand(ph),
		Args:    newInitContainerArgs(ph),
		VolumeMounts: []corev1.VolumeMount{
			{
				Name:      photonVolumeName,
				MountPath: photonVolumeMountPath,
			},
		},
	}
}

func newMainContainerCommand(ph *Photon) []string {
	return []string{"sh"}
}

func newMainContainerArgs(ph *Photon) []string {
	leptonCmd := fmt.Sprintf("lepton photon prepare -f %s; lepton photon run -f %[1]s", photonDestPath(ph))
	return []string{"-c", leptonCmd}
}

func (ld *LeptonDeployment) merge(p *LeptonDeployment) {
	if p.PhotonID != "" {
		ld.PhotonID = p.PhotonID
	}
	if p.ResourceRequirement.MinReplicas > 0 {
		ld.ResourceRequirement.MinReplicas = p.ResourceRequirement.MinReplicas
	}
}

func createDeploymentPodSpec(ld *LeptonDeployment) (*corev1.PodSpec, error) {
	photonMapRWLock.RLock()
	ph := photonById[ld.PhotonID]
	photonMapRWLock.RUnlock()
	if ph == nil {
		return nil, fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}

	// Define the shared volume
	sharedVolume := corev1.Volume{
		Name: photonVolumeName,
		VolumeSource: corev1.VolumeSource{
			EmptyDir: &corev1.EmptyDirVolumeSource{},
		},
	}

	cpu := resource.NewScaledQuantity(int64(ld.ResourceRequirement.CPU*1000), -3)
	// TODO: we may want to change memory to BinarySI
	memory := resource.NewScaledQuantity(ld.ResourceRequirement.Memory, 6)
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
	if ld.ResourceRequirement.AcceleratorType != "" && ld.ResourceRequirement.AcceleratorNum > 0 {
		// if gpu is enabled, set gpu resource limit and node selector
		resources.Limits[nvidiaGPUResourceName] = *resource.NewQuantity(int64(ld.ResourceRequirement.AcceleratorNum), resource.DecimalSI)
		nodeSelector[nvidiaGPUProductLabelKey] = ld.ResourceRequirement.AcceleratorType
	}

	container := corev1.Container{
		Name:            mainContainerName,
		Image:           ph.Image,
		ImagePullPolicy: corev1.PullAlways,
		Command:         newMainContainerCommand(ph),
		Args:            newMainContainerArgs(ph),
		Resources:       resources,
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
		InitContainers:     []corev1.Container{newInitContainer(ph)},
		Containers:         []corev1.Container{container},
		Volumes:            []corev1.Volume{sharedVolume},
		ServiceAccountName: *serviceAccountNameFlag,
		NodeSelector:       nodeSelector,
	}

	return spec, nil
}

func (ld *LeptonDeployment) validateDeployment() error {
	if ld.ResourceRequirement.CPU <= 0 {
		return fmt.Errorf("cpu must be positive")
	}
	if ld.ResourceRequirement.Memory <= 0 {
		return fmt.Errorf("memory must be positive")
	}
	if ld.ResourceRequirement.MinReplicas <= 0 {
		return fmt.Errorf("min replicas must be positive")
	}
	photonMapRWLock.RLock()
	ph := photonById[ld.PhotonID]
	photonMapRWLock.RUnlock()
	if ph == nil {
		return fmt.Errorf("photon %s does not exist", ld.PhotonID)
	}
	return nil
}

func (ld *LeptonDeployment) validatePatch() error {
	valid := false
	if ld.ResourceRequirement.MinReplicas > 0 {
		valid = true
	}
	if ld.PhotonID != "" {
		photonMapRWLock.RLock()
		ph := photonById[ld.PhotonID]
		photonMapRWLock.RUnlock()
		if ph == nil {
			return fmt.Errorf("photon %s does not exist", ld.PhotonID)
		}
		valid = true
	}
	if !valid {
		return fmt.Errorf("no valid field to patch")
	}
	return nil
}
