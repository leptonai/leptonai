package k8s

import (
	"log"
	"os"
	"sync"

	goutil "github.com/leptonai/lepton/go-pkg/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	mothershipv1alpha1 "github.com/leptonai/lepton/mothership/crd/api/v1alpha1"

	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/client-go/kubernetes"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/config"
)

var scheme *runtime.Scheme = runtime.NewScheme()

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(leptonaiv1alpha1.AddToScheme(scheme))
	utilruntime.Must(mothershipv1alpha1.AddToScheme(scheme))
}

var (
	defaultClientMu sync.Mutex
	defaultClient   client.WithWatch
)

// LoadDefaultClient loads the default Kubernetes client
// and returns a client with watch interface.
func LoadDefaultClient() (client.WithWatch, error) {
	defaultClientMu.Lock()
	defer defaultClientMu.Unlock()

	if defaultClient != nil {
		return defaultClient, nil
	}

	config, err := config.GetConfig()
	if err != nil {
		goutil.Logger.Errorw("failed to load k8s config",
			"error", err,
		)
		return nil, err
	}

	defaultClient, err = client.NewWithWatch(config, client.Options{Scheme: scheme})
	if err != nil {
		goutil.Logger.Errorw("failed to create k8s client",
			"error", err,
		)
	}
	return defaultClient, err
}

// MustLoadDefaultClient loads the default Kubernetes client
// and panics if it fails.
func MustLoadDefaultClient() client.WithWatch {
	c, err := LoadDefaultClient()
	if err != nil {
		goutil.Logger.Fatalw("failed to load k8s client",
			"error", err,
		)
	}
	return c
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
