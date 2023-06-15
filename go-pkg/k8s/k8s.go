package k8s

import (
	"log"
	"os"

	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
	mothershipv1alpha1 "github.com/leptonai/lepton/lepton-mothership/crd/api/v1alpha1"

	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/client-go/kubernetes"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/config"
)

var (
	Config *rest.Config
	Client client.WithWatch
)

func init() {
	// TODO: handle the errors
	Config, _ = config.GetConfig()
	scheme := runtime.NewScheme()
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(leptonaiv1alpha1.AddToScheme(scheme))
	utilruntime.Must(mothershipv1alpha1.AddToScheme(scheme))
	Client, _ = client.NewWithWatch(Config, client.Options{Scheme: scheme})
}

func MustInitK8sClientSetWithConfig() (*kubernetes.Clientset, *rest.Config) {
	// Load Kubernetes configuration from default location or specified kubeconfig file
	config, err := clientcmd.BuildConfigFromFlags("", os.Getenv("KUBECONFIG"))
	if err != nil {
		log.Fatalln(err)
	}
	// Create a Kubernetes client
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		log.Fatalln(err)
	}
	return clientset, config
}
func MustInitK8sClientSet() *kubernetes.Clientset {
	c, _ := MustInitK8sClientSetWithConfig()
	return c
}
