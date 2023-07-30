// Package get implements get command.
package get

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/leptonai/lepton/mothership/cmd/mothership/common"

	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

var (
	namespace string
	svcName   string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters services get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get service",
		Run:   getFunc,
	}

	cmd.PersistentFlags().StringVarP(&namespace, "namespace", "n", "kubecost", "Namespace that the service belongs to")
	cmd.PersistentFlags().StringVarP(&svcName, "service-name", "s", "cost-analyzer-cost-analyzer", "Service name")

	return cmd
}

func getFunc(cmd *cobra.Command, args []string) {
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

	colums := []string{"service name", "port name", "service endpoint"}
	rows := make([][]string, 0)

	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	svcList, err := clientset.CoreV1().Services(namespace).List(ctx, v1.ListOptions{})
	cancel()
	if err != nil {
		log.Fatal(err)
	}

	for _, svc := range svcList.Items {
		if svc.Name != svcName {
			continue
		}

		for _, port := range svc.Spec.Ports {
			rows = append(rows,
				[]string{
					svc.Name,
					port.Name,

					// port that's exposed by this service
					// e.g., http://kube-prometheus-stack-grafana.kube-prometheus-stack.svc.cluster.local:80
					fmt.Sprintf("http://%s.%s.svc.cluster.local:%d", svc.Name, namespace, port.Port),
				})
		}
	}

	buf := bytes.NewBuffer(nil)
	tb := tablewriter.NewWriter(buf)
	tb.SetAutoWrapText(false)
	tb.SetAlignment(tablewriter.ALIGN_LEFT)
	tb.SetCenterSeparator("*")
	tb.SetHeader(colums)
	tb.AppendBulk(rows)
	tb.Render()
	fmt.Println(buf.String())
}
