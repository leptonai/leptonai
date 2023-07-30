// Package list implements list command.
package list

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
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/selection"
	"k8s.io/client-go/kubernetes"
)

// mothership clusters services --kubeconfig /tmp/gh015.kubeconfig list
var (
	output string
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "mothership clusters get" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all the services (either EKS/*) for a given cluster",
		Run:   listFunc,
	}
	cmd.PersistentFlags().StringVarP(&output, "output", "o", "table", "Output format, either 'rawjson' or 'table'")
	return cmd
}

func listFunc(cmd *cobra.Command, args []string) {
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

	colums := []string{"provider", "namespace", "service name", "pod", "port name", "port", "target port"}
	rows := make([][]string, 0)
	for namespace, queryingSvcs := range common.EKSLeptonServices {
		ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
		svcList, err := clientset.CoreV1().Services(namespace).List(ctx, v1.ListOptions{})
		cancel()
		if err != nil {
			log.Fatal(err)
		}

		for _, svc := range svcList.Items {
			if _, ok := queryingSvcs[svc.Name]; !ok {
				continue
			}

			labelSelector := labels.NewSelector()
			for k, v := range svc.Spec.Selector {
				selector, err := labels.NewRequirement(k, selection.Equals, []string{v})
				if err != nil {
					log.Fatal(err)
				}
				labelSelector = labelSelector.Add(*selector)
			}

			ctx, cancel = context.WithTimeout(context.Background(), time.Minute)
			podList, err := clientset.CoreV1().Pods(namespace).List(ctx, v1.ListOptions{
				LabelSelector: labelSelector.String(),
			})
			cancel()
			if err != nil {
				log.Fatal(err)
			}
			if len(podList.Items) != 1 {
				log.Fatalf("expected 1 matching pod for %q, got %d pods", labelSelector.String(), len(podList.Items))
			}

			pod := podList.Items[0]
			for _, port := range svc.Spec.Ports {
				rows = append(rows,
					[]string{
						"eks",
						namespace,
						svc.Name,
						pod.Name,
						port.Name,

						// port that's exposed by this service
						// e.g., http://kube-prometheus-stack-grafana.kube-prometheus-stack.svc.cluster.local:80
						fmt.Sprintf(":%d", port.Port),

						// port to access on the pods targeted by the service
						// e.g., kubectl -n kube-prometheus-stack port-forward $POD 3001:3000
						// e.g., kubectl -n kube-prometheus-stack port-forward $POD 3001:[TARGET PORT]
						fmt.Sprintf(":%d", port.TargetPort.IntVal),
					})
			}
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
