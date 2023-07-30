// Package portforward implements port-forward command.
package portforward

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/mothership/cmd/mothership/common"

	"github.com/spf13/cobra"
	"k8s.io/client-go/kubernetes"
)

var (
	namespace string
	svcName   string
	svcPort   int
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters services port-forward" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "port-forward",
		Short: "Forwards the pod port for the service",
		Run:   portForwardFunc,
	}

	cmd.PersistentFlags().StringVarP(&namespace, "namespace", "n", "kubecost", "Namespace that the service belongs to")
	cmd.PersistentFlags().StringVarP(&svcName, "service-name", "s", "cost-analyzer-cost-analyzer", "Service name")
	cmd.PersistentFlags().IntVar(&svcPort, "service-port", 3000, "Service port to forward (either port or target port)")

	return cmd
}

func portForwardFunc(cmd *cobra.Command, args []string) {
	kfv := common.ReadKubeconfigFromFlag(cmd)
	kubeconfig := os.Getenv("KUBECONFIG")
	if kfv != "" {
		kubeconfig = kfv
	}
	restConfig, clusterARN, err := common.BuildRestConfig(kubeconfig)
	if err != nil {
		log.Fatalf("error building config from kubeconfig %v", err)
	}
	log.Printf("listing services for cluster %q", clusterARN)

	clientset, err := kubernetes.NewForConfig(restConfig)
	if err != nil {
		log.Fatal(err)
	}

	// port to access on the pods targeted by the service
	// e.g., kubectl -n kube-prometheus-stack port-forward $POD 3001:3000
	// e.g., kubectl -n kube-prometheus-stack port-forward $POD 3001:[TARGET PORT]
	log.Printf("port-forwarding the service %q for the service port %d", svcName, svcPort)

	// ref. https://github.com/kubecost/kubectl-cost/blob/main/pkg/cmd/aggregatedcommandbuilder.go
	// ref. https://github.com/kubecost/kubectl-cost/blob/main/pkg/query/allocation.go
	// ref. https://github.com/kubecost/kubectl-cost/blob/main/pkg/query/portforward.go
	// set timeout for querying pods to get the service information
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	fwd, err := service.NewPortForwardQuerier(
		ctx,
		clientset,
		restConfig,
		namespace,
		svcName,
		int(svcPort),
	)
	cancel()
	if err != nil {
		log.Fatalf("failed to create port forwarder for service %v", err)
	}

	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGTERM, syscall.SIGINT)

	log.Printf("forwarding %q to %q", svcName, fwd.BaseQueryURL)
	sig := <-sigs
	log.Printf("received signal %s", sig)
	fwd.Stop()
}
