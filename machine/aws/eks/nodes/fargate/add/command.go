// Package add implements add command.
package add

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strings"
	"time"

	"github.com/leptonai/lepton/go-pkg/aws"
	"github.com/leptonai/lepton/go-pkg/aws/ec2"
	"github.com/leptonai/lepton/go-pkg/aws/eks"
	"github.com/leptonai/lepton/machine/aws/common"
	mothership_common "github.com/leptonai/lepton/mothership/cmd/mothership/common"

	"github.com/spf13/cobra"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	apply_core_v1 "k8s.io/client-go/applyconfigurations/core/v1"
	apply_meta_v1 "k8s.io/client-go/applyconfigurations/meta/v1"
	"k8s.io/client-go/kubernetes"
	"sigs.k8s.io/yaml"
)

var (
	region      string
	clusterName string

	eniID        string
	keep         bool
	keepInterval time.Duration
)

func init() {
	cobra.EnablePrefixMatching = true
}

// NewCommand implements "machine aws nodes fargate add" command.
func NewCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:        "add",
		Short:      "Implements add sub-commands (manually add/apply fargate node object)",
		Aliases:    []string{"a", "ad", "apply", "create"},
		SuggestFor: []string{"a", "ad", "apply", "create"},
		Run:        addFunc,
	}

	cmd.PersistentFlags().StringVarP(&region, "region", "r", "us-east-1", "AWS region")
	cmd.PersistentFlags().StringVarP(&clusterName, "cluster-name", "c", "", "AWS EKS cluster name")

	cmd.PersistentFlags().StringVarP(&eniID, "eni-id", "e", "", "AWS ENI")
	cmd.PersistentFlags().BoolVar(&keep, "keep", false, "Set true to keep applying the node object (useful to keep the node alive while kubelet is still being ready)")
	cmd.PersistentFlags().DurationVar(&keepInterval, "keep-interval", 30*time.Second, "interval to send node apply request")

	return cmd
}

func addFunc(cmd *cobra.Command, args []string) {
	region, err := common.ReadRegion(cmd)
	if err != nil {
		slog.Error("error reading region",
			"error", err,
		)
		os.Exit(1)
	}

	cfg, err := aws.New(&aws.Config{
		Region: region,
	})
	if err != nil {
		slog.Error("failed to create aws config",
			"error", err,
		)
		os.Exit(1)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	cluster, err := eks.GetCluster(ctx, cfg, clusterName)
	cancel()
	if err != nil {
		slog.Error("failed to get EKS cluster",
			"error", err,
		)
		os.Exit(1)
	}

	ctx, cancel = context.WithTimeout(context.Background(), 10*time.Second)
	eni, err := ec2.GetENI(ctx, cfg, eniID)
	cancel()
	if err != nil {
		slog.Error("failed to get ENI",
			"error", err,
		)
		os.Exit(1)
	}

	if cluster.VPCID != *eni.VpcId {
		slog.Error("failed to get ENI",
			"eks-vpc", cluster.VPCID,
			"eni-vpc", *eni.VpcId,
		)
		os.Exit(1)
	}

	privateDNS := *eni.PrivateDnsName
	nodeHostname := "fargate-" + strings.ReplaceAll(privateDNS, ".ec2.internal", fmt.Sprintf(".%s.compute.internal", region))
	slog.Info("creating a fargate node with ENI",
		"private-dns", privateDNS,
		"node-hostname", nodeHostname,
	)

	kcfg, err := cluster.Kubeconfig()
	if err != nil {
		slog.Error("failed to get EKS cluster kubeconfig",
			"error", err,
		)
		os.Exit(1)
	}
	b, err := yaml.Marshal(kcfg)
	if err != nil {
		slog.Error("failed to marshal kubeconfig",
			"error", err,
		)
		os.Exit(1)
	}

	f, err := os.CreateTemp(os.TempDir(), "farget-virtual-node")
	if err != nil {
		slog.Error("failed to create a temp file",
			"error", err,
		)
		os.Exit(1)
	}
	if _, err = f.Write(b); err != nil {
		slog.Error("failed to write kubeconfig to a temp file",
			"error", err,
		)
		os.Exit(1)
	} else {
		slog.Info("successfully wrote kubeconfig to a temp file",
			"path", f.Name(),
		)
	}
	if err = f.Sync(); err != nil {
		slog.Error("failed to sync kubeconfig to a temp file",
			"error", err,
		)
		os.Exit(1)
	}
	kubeconfigPath := f.Name()

	restConfig, clusterARN, err := mothership_common.BuildRestConfig(kubeconfigPath)
	if err != nil {
		slog.Error("failed to build rest config from kubeconfig",
			"error", err,
		)
		os.Exit(1)
	}
	slog.Info("successfully built rest config from kubeconfig", "arn", clusterARN)

	clientset, err := kubernetes.NewForConfig(restConfig)
	if err != nil {
		slog.Error("failed to create kubernetes clientset",
			"error", err,
		)
		os.Exit(1)
	}

	nodeObj := apply_core_v1.NodeApplyConfiguration{
		TypeMetaApplyConfiguration: apply_meta_v1.TypeMetaApplyConfiguration{
			APIVersion: newString("v1"),
			Kind:       newString("Node"),
		},
		ObjectMetaApplyConfiguration: &apply_meta_v1.ObjectMetaApplyConfiguration{
			Name: newString(nodeHostname),
			Annotations: map[string]string{
				"node.alpha.kubernetes.io/ttl": "0",
			},
			Labels: map[string]string{
				"alpha.service-controller.kubernetes.io/exclude-balancer": "true",
				"beta.kubernetes.io/os":                                   "linux",
				"kubernetes.io/hostname":                                  nodeHostname,
				"kubernetes.io/role":                                      "agent",
			},
		},
		Spec: &apply_core_v1.NodeSpecApplyConfiguration{
			Taints: []apply_core_v1.TaintApplyConfiguration{
				{
					Key:    newString("virtual-kubelet.io/provider"),
					Value:  newString("ec2"),
					Effect: &noSchedule,
				},
			},
		},
		Status: &apply_core_v1.NodeStatusApplyConfiguration{
			Allocatable: &corev1.ResourceList{
				corev1.ResourceCPU:     resource.MustParse("120"),
				corev1.ResourceMemory:  resource.MustParse("400Gi"),
				corev1.ResourcePods:    resource.MustParse("200"),
				corev1.ResourceStorage: resource.MustParse("400Gi"),
			},
			Capacity: &corev1.ResourceList{
				corev1.ResourceCPU:     resource.MustParse("120"),
				corev1.ResourceMemory:  resource.MustParse("400Gi"),
				corev1.ResourcePods:    resource.MustParse("200"),
				corev1.ResourceStorage: resource.MustParse("400Gi"),
			},
			Conditions: generateNodeConditions(time.Now()),
			DaemonEndpoints: &apply_core_v1.NodeDaemonEndpointsApplyConfiguration{
				KubeletEndpoint: &apply_core_v1.DaemonEndpointApplyConfiguration{
					Port: newInt32(0),
				},
			},
			NodeInfo: &apply_core_v1.NodeSystemInfoApplyConfiguration{
				Architecture:    newString("amd64"),
				OperatingSystem: newString("Linux"),
			},
		},
	}

	for i := 0; ; i++ {
		// e.g., "2023-08-16T09:34:07Z"
		now := time.Now().UTC()
		ts := now.Format("2006-01-02T15:04:05Z")
		slog.Info("applying kubernetes node object",
			"timestamp", ts,
		)
		nodeObj.Status.Conditions = generateNodeConditions(now)

		b, err := yaml.Marshal(nodeObj)
		if err != nil {
			slog.Error("failed to marshal node object",
				"error", err,
			)
			os.Exit(1)
		}
		fmt.Printf("\napplying node:\n\n%s\n\n", string(b))

		ctx, cancel = context.WithTimeout(context.Background(), 10*time.Second)
		_, err = clientset.CoreV1().Nodes().Apply(
			ctx,
			&nodeObj,
			metav1.ApplyOptions{
				FieldManager: "application/apply-patch",
			},
		)
		cancel()
		if err != nil {
			slog.Error("failed to apply kubernetes node object",
				"error", err,
			)
			os.Exit(1)
		}

		if !keep {
			break
		}

		time.Sleep(keepInterval)
	}
}

func newInt32(i int32) *int32 {
	return &i
}

func newString(s string) *string {
	return &s
}

var (
	noSchedule             = corev1.TaintEffectNoSchedule
	conditionTrue          = corev1.ConditionTrue
	conditionFalse         = corev1.ConditionFalse
	nodeReady              = corev1.NodeReady
	nodePIDPressure        = corev1.NodePIDPressure
	nodeMemoryPressure     = corev1.NodeMemoryPressure
	nodeDiskPressure       = corev1.NodeDiskPressure
	nodeNetworkUnavailable = corev1.NodeNetworkUnavailable
	nodeKubeletConfigOK    = corev1.NodeConditionType("KubeletConfigOk")
)

func generateNodeConditions(ts time.Time) []apply_core_v1.NodeConditionApplyConfiguration {
	heartbeat := metav1.NewTime(ts)
	lastTransition := metav1.NewTime(ts.Add(-time.Second))

	return []apply_core_v1.NodeConditionApplyConfiguration{
		{
			Type:               &nodeReady,
			Status:             &conditionTrue,
			Message:            newString("ok"),
			LastHeartbeatTime:  &heartbeat,
			LastTransitionTime: &lastTransition,
		},
		{
			Type:               &nodePIDPressure,
			Status:             &conditionFalse,
			Message:            newString("ok"),
			LastHeartbeatTime:  &heartbeat,
			LastTransitionTime: &lastTransition,
		},
		{
			Type:               &nodeMemoryPressure,
			Status:             &conditionFalse,
			Message:            newString("ok"),
			LastHeartbeatTime:  &heartbeat,
			LastTransitionTime: &lastTransition,
		},
		{
			Type:               &nodeDiskPressure,
			Status:             &conditionFalse,
			Message:            newString("ok"),
			LastHeartbeatTime:  &heartbeat,
			LastTransitionTime: &lastTransition,
		},
		{
			Type:               &nodeNetworkUnavailable,
			Status:             &conditionFalse,
			Message:            newString("ok"),
			LastHeartbeatTime:  &heartbeat,
			LastTransitionTime: &lastTransition,
		},
		{
			Type:               &nodeKubeletConfigOK,
			Status:             &conditionTrue,
			Message:            newString("ok"),
			LastHeartbeatTime:  &heartbeat,
			LastTransitionTime: &lastTransition,
		},
	}
}
