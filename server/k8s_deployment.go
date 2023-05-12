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

func patchDeployment(ld *LeptonDeployment) error {
	// Create a Kubernetes client
	clientset := mustInitK8sClientSet()

	// Patch the deployment
	deployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Get(context.TODO(), ld.Name, metav1.GetOptions{})
	if err != nil {
		return err
	}
	deployment.Spec.Replicas = int32Ptr(int32(ld.ResourceRequirement.MinReplicas))
	_, err = clientset.AppsV1().Deployments(deploymentNamespace).Update(context.TODO(), deployment, metav1.UpdateOptions{
		FieldManager: "lepton",
	})

	if err != nil {
		return err
	}

	return nil
}

func createDeployment(ld *LeptonDeployment, ph *Photon, or metav1.OwnerReference) error {
	// Create a Kubernetes client
	clientset := mustInitK8sClientSet()

	// Define the shared volume
	photonVolumeName := "photon"
	photonVolumeMountPath := "/photon"
	awsCredVolumeName := "aws-credentials"
	awsCredVolumeMountPath := "/root/.aws"
	sharedVolume := corev1.Volume{
		Name: photonVolumeName,
		VolumeSource: corev1.VolumeSource{
			EmptyDir: &corev1.EmptyDirVolumeSource{},
		},
	}
	awsCredentialsVolume := corev1.Volume{
		Name: awsCredVolumeName,
		VolumeSource: corev1.VolumeSource{
			Secret: &corev1.SecretVolumeSource{
				SecretName: "aws-credentials",
			},
		},
	}

	// use path.join?
	s3URL := fmt.Sprintf("s3://%s/%s/%s", *bucketNameFlag, *photonPrefixFlag, joinNameByDash(ph.Name, ph.ID))
	dest := photonVolumeMountPath + "/" + joinNameByDash(ph.Name, ph.ID)

	// Define the init container
	initContainer := corev1.Container{
		Name:  "evn-preparation",
		Image: awscliImageURL,
		// TODO support other clouds
		// aws s3 cp s3://my-bucket/example.txt ./example.txt
		Command: []string{"aws", "s3", "cp", s3URL, dest},
		VolumeMounts: []corev1.VolumeMount{
			{
				Name:      photonVolumeName,
				MountPath: photonVolumeMountPath,
			},
			{
				Name:      awsCredVolumeName,
				MountPath: awsCredVolumeMountPath,
			},
		},
	}

	cpu := resource.NewScaledQuantity(int64(ld.ResourceRequirement.CPU*1000), -3)
	// TODO: we may want to change memory to BinarySI
	memory := resource.NewScaledQuantity(ld.ResourceRequirement.Memory, 6)
	// Define the main container
	container := corev1.Container{
		Name:            "main-container",
		Image:           ph.Image,
		ImagePullPolicy: corev1.PullAlways,
		Command:         []string{"lepton", "photon", "run"},
		Args:            []string{"-f", dest},
		Resources: corev1.ResourceRequirements{
			Requests: corev1.ResourceList{
				corev1.ResourceCPU:    *cpu,
				corev1.ResourceMemory: *memory,
			},
			Limits: corev1.ResourceList{
				corev1.ResourceCPU:    *cpu,
				corev1.ResourceMemory: *memory,
				// TODO add GPU
			},
		},
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

	// Define the pod template
	template := corev1.PodTemplateSpec{
		ObjectMeta: metav1.ObjectMeta{
			Labels: map[string]string{
				"photon": joinNameByDash(ph.Name, ph.ID),
			},
		},
		Spec: corev1.PodSpec{
			InitContainers: []corev1.Container{initContainer},
			Containers:     []corev1.Container{container},
			Volumes:        []corev1.Volume{sharedVolume, awsCredentialsVolume},
		},
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
					"photon": joinNameByDash(ph.Name, ph.ID),
				},
			},
			Template: template,
		},
	}

	// Create the deployment
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
	DeploymentStateEmpty            DeploymentState = ""
	DeploymentStateRunning          DeploymentState = "Running"
	DeploymentStatePartiallyRunning DeploymentState = "Partially Running"
	DeploymentStateNotReady         DeploymentState = "Not Ready"
	DeploymentStateStarting         DeploymentState = "Starting"
	DeploymentStatePatching         DeploymentState = "Patching"
	DeploymentStateUnknown          DeploymentState = "Unknown"
)

func deploymentState(names ...string) []DeploymentState {
	// Create a Kubernetes client
	clientset := mustInitK8sClientSet()

	states := make([]DeploymentState, 0, len(names))
	for _, name := range names {
		// Get the deployment
		deployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Get(context.TODO(), name, metav1.GetOptions{})
		if err != nil {
			states = append(states, DeploymentStateUnknown)
			continue
		}

		// Get the deployment status
		status := deployment.Status
		if status.Replicas == status.ReadyReplicas {
			states = append(states, DeploymentStateRunning)
		} else if status.ReadyReplicas > 0 {
			states = append(states, DeploymentStatePartiallyRunning)
		} else {
			states = append(states, DeploymentStateNotReady)
		}
	}

	return states
}
