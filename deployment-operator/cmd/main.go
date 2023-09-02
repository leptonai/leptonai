/*
Copyright 2023.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package main

import (
	"context"
	"flag"
	"os"
	"strings"
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	"github.com/leptonai/lepton/deployment-operator/internal/controller"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	// Import all Kubernetes client auth plugins (e.g. Azure, GCP, OIDC, etc.)
	// to ensure that exec-entrypoint and run can make use of them.
	"github.com/solo-io/gloo/projects/gloo/cli/pkg/helpers"
	_ "go.uber.org/automaxprocs"
	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	_ "k8s.io/client-go/plugin/pkg/client/auth"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/cache"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	//+kubebuilder:scaffold:imports
)

var (
	scheme   = runtime.NewScheme()
	setupLog = ctrl.Log.WithName("setup")
)

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))

	utilruntime.Must(leptonaiv1alpha1.AddToScheme(scheme))
	//+kubebuilder:scaffold:scheme
}

func main() {
	var metricsAddr string
	var enableLeaderElection bool
	var probeAddr string
	var namespace string
	var namespaces string
	var lbType string
	flag.StringVar(&metricsAddr, "metrics-bind-address", ":8080", "The address the metric endpoint binds to.")
	flag.StringVar(&probeAddr, "health-probe-bind-address", ":8081", "The address the probe endpoint binds to.")
	flag.BoolVar(&enableLeaderElection, "leader-elect", false,
		"Enable leader election for controller manager. "+
			"Enabling this will ensure there is only one active controller manager.")
	flag.StringVar(&namespace, "namespace", "", "The namespace to watch for LeptonDeployment objects. Can only set one of namespace or namespaces.")
	flag.StringVar(&namespaces, "namespaces", "", "The list of namespaces separated by comma to watch for LeptonDeployment objects. Defaults to all namespaces.")
	flag.StringVar(&lbType, "lb-type", string(leptonaiv1alpha1.WorkspaceLBTypeDedicated), "If the deployments should shared LB infra")
	opts := zap.Options{
		Development: true,
	}
	opts.BindFlags(flag.CommandLine)
	flag.Parse()

	ctrl.SetLogger(zap.New(zap.UseFlagOptions(&opts)))

	if namespaces != "" && namespace != "" {
		goutil.Logger.Fatalw("can only set one of namespace or namespaces",
			"namespace", namespace,
			"namespaces", namespaces,
		)
	}
	var namespaceList []string
	if namespace != "" {
		namespaceList = []string{namespace}
	} else {
		// if namespaces is empty (""), watch all namespaces by setting namespaceList to []string{""}
		namespaceList = strings.Split(namespace, ",")
	}

	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
		Scheme:                 scheme,
		MetricsBindAddress:     metricsAddr,
		Cache:                  cache.Options{Namespaces: namespaceList},
		Port:                   9443,
		HealthProbeBindAddress: probeAddr,
		LeaderElection:         enableLeaderElection,
		LeaderElectionID:       "aba1f66b.lepton.ai",
		// LeaderElectionReleaseOnCancel defines if the leader should step down voluntarily
		// when the Manager ends. This requires the binary to immediately end when the
		// Manager is stopped, otherwise, this setting is unsafe. Setting this significantly
		// speeds up voluntary leader transitions as the new leader don't have to wait
		// LeaseDuration time first.
		//
		// In the default scaffold provided, the program ends immediately after
		// the manager stops, so would be fine to enable this option. However,
		// if you are doing or is intended to do any operation such as perform cleanups
		// after the manager stops then its usage might be unsafe.
		// LeaderElectionReleaseOnCancel: true,
	})
	if err != nil {
		setupLog.Error(err, "unable to start manager")
		os.Exit(1)
	}

	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	defer cancel()
	ldr := &controller.LeptonDeploymentReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
		LBType: leptonaiv1alpha1.LeptonWorkspaceLBType(lbType),
		GlooClients: controller.GlooClients{
			VirtualServiceClient: helpers.MustMultiNamespacedVirtualServiceClient(ctx, namespaceList),
			RouteTableClient:     helpers.MustMultiNamespacedRouteTableClient(ctx, namespaceList),
			UpstreamClient:       helpers.MustMultiNamespacedUpstreamClient(ctx, namespaceList),
		},
	}
	go ldr.CleanupBadPodsPeriodically(namespaceList)

	if err = (ldr).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "LeptonDeployment")
		os.Exit(1)
	}

	//+kubebuilder:scaffold:builder

	if err := mgr.AddHealthzCheck("healthz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up health check")
		os.Exit(1)
	}
	if err := mgr.AddReadyzCheck("readyz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up ready check")
		os.Exit(1)
	}

	setupLog.Info("starting manager")
	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setupLog.Error(err, "problem running manager")
		os.Exit(1)
	}
}
