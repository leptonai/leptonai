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

package controller

import (
	"context"
	"errors"
	"fmt"
	"time"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	domainname "github.com/leptonai/lepton/go-pkg/domain-name"
	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	soloclients "github.com/solo-io/solo-kit/pkg/api/v1/clients"
	gloocore "github.com/solo-io/solo-kit/pkg/api/v1/resources/core"
	glooerrors "github.com/solo-io/solo-kit/pkg/errors"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	networkingv1 "k8s.io/api/networking/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/handler"
)

// LeptonDeploymentReconciler reconciles a LeptonDeployment object
type LeptonDeploymentReconciler struct {
	client.Client
	GlooClients
	Scheme *runtime.Scheme
	LBType leptonaiv1alpha1.LeptonWorkspaceLBType
}

//+kubebuilder:rbac:groups=lepton.ai,resources=leptondeployments,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=lepton.ai,resources=leptondeployments/status,verbs=get;update;patch
//+kubebuilder:rbac:groups=lepton.ai,resources=leptondeployments/finalizers,verbs=update

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
// TODO(user): Modify the Reconcile function to compare the state specified by
// the LeptonDeployment object against the actual cluster state, and then
// perform operations to make the cluster state reflect the state specified by
// the user.
//
// For more details, check Reconcile and its Result here:
// - https://pkg.go.dev/sigs.k8s.io/controller-runtime@v0.14.4/pkg/reconcile
func (r *LeptonDeploymentReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	goutil.Logger.Infow("reconciling LeptonDeployment...",
		"namespace", req.Namespace,
		"name", req.Name,
	)

	ld, err := r.getLeptonDeployment(ctx, req)
	if err != nil {
		goutil.Logger.Errorw("failed to get LeptonDeployment",
			"namespace", req.Namespace,
			"name", req.Name,
			"error", err,
		)
		return ctrl.Result{Requeue: true, RequeueAfter: 10 * time.Second}, err
	}
	// LeptonDeployment has been deleted
	if ld == nil {
		goutil.Logger.Infow("LeptonDeployment has been deleted",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		return ctrl.Result{}, nil
	}
	// Check the deployment status
	if err := r.updateDeploymentStatus(ctx, req, ld); err != nil {
		goutil.Logger.Errorw("failed to update LeptonDeployment status",
			"namespace", req.Namespace,
			"name", req.Name,
			"error", err,
		)
		return ctrl.Result{Requeue: true, RequeueAfter: 10 * time.Second}, err
	}
	// LeptonDeployment is marked for deletion
	if !ld.DeletionTimestamp.IsZero() {
		goutil.Logger.Infow("LeptonDeployment marked for deletion",
			"namespace", req.Namespace,
			"name", req.Name,
		)

		if err := r.finalize(ctx, req, ld); err != nil {
			goutil.Logger.Errorw("failed to delete LeptonDeployment",
				"namespace", req.Namespace,
				"name", req.Name,
				"error", err,
			)
			return ctrl.Result{Requeue: true, RequeueAfter: 10 * time.Second}, err
		}
		goutil.Logger.Infow("LeptonDeployment deleted",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		return ctrl.Result{}, nil
	}
	// Add our finalizer if it does not exist
	if !goutil.ContainsString(ld.GetFinalizers(), leptonaiv1alpha1.DeletionFinalizerName) {
		ld.SetFinalizers(append(ld.GetFinalizers(), leptonaiv1alpha1.DeletionFinalizerName))
		if err := r.Update(ctx, ld); err != nil {
			goutil.Logger.Errorw("failed to add finalizer to LeptonDeployment",
				"namespace", req.Namespace,
				"name", req.Name,
				"error", err,
			)
			return ctrl.Result{Requeue: true, RequeueAfter: 10 * time.Second}, err
		}
	}
	// Reconcile resources
	if err := r.createOrUpdateResources(ctx, req, ld); err != nil {
		goutil.Logger.Warnw("failed to create or update resources, retrying...",
			"namespace", req.Namespace,
			"name", req.Name,
			"error", err,
		)
		return ctrl.Result{Requeue: true, RequeueAfter: 10 * time.Second}, err
	}
	return ctrl.Result{}, nil
}

func (r *LeptonDeploymentReconciler) getLeptonDeployment(ctx context.Context, req ctrl.Request) (*leptonaiv1alpha1.LeptonDeployment, error) {
	ld := &leptonaiv1alpha1.LeptonDeployment{}
	if err := r.Client.Get(ctx, req.NamespacedName, ld); err != nil {
		if !apierrors.IsNotFound(err) {
			return nil, err
		}
		return nil, nil
	}
	return ld, nil
}

func (r *LeptonDeploymentReconciler) getDeployment(ctx context.Context, req ctrl.Request) (*appsv1.Deployment, error) {
	deployment := &appsv1.Deployment{}
	if err := r.Client.Get(ctx, req.NamespacedName, deployment); err != nil {
		return nil, err
	}
	return deployment, nil
}

func (r *LeptonDeploymentReconciler) createOrUpdateResources(ctx context.Context, req ctrl.Request,
	ld *leptonaiv1alpha1.LeptonDeployment) error {
	ldOr := getOwnerRefFromLeptonDeployment(ld)
	glooOr := getGlooOwnerRefFromLeptonDeployment(ld)
	_, err := r.createOrUpdateService(ctx, req, ld, []metav1.OwnerReference{*ldOr})
	if err != nil {
		return errors.New("failed to create or update Service: " + err.Error())
	}
	_, err = r.createOrUpdateDeployment(ctx, req, ld, []metav1.OwnerReference{*ldOr})
	if err != nil {
		return errors.New("failed to create or update Deployment: " + err.Error())
	}
	if err := r.createOrUpdateIngress(ctx, req, ld, []metav1.OwnerReference{*ldOr}); err != nil {
		return errors.New("failed to create or update Ingress: " + err.Error())
	}
	if err := r.createOrUpdateLoadBalancerRules(ctx, req, ld, []*gloocore.Metadata_OwnerReference{glooOr}); err != nil {
		return errors.New("failed to create or update shared load balancer: " + err.Error())
	}

	return nil
}

func (r *LeptonDeploymentReconciler) updateDeploymentStatus(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment) error {
	if ld == nil {
		return nil
	}
	if !ld.DeletionTimestamp.IsZero() {
		ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateDeleting
		ld.Status.Endpoint.ExternalEndpoint = ""
	} else {
		deployment, err := r.getDeployment(ctx, req)
		if err != nil {
			if apierrors.IsNotFound(err) {
				ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateStarting
			} else {
				return err
			}
		} else {
			ld.Status.State = transitionState(deployment.Status.Replicas, deployment.Status.ReadyReplicas, ld.Status.State)
		}
		if r.LBType == leptonaiv1alpha1.WorkspaceLBTypeShared {
			ld.Status.Endpoint.ExternalEndpoint = "https://" + domainname.New(ld.Spec.WorkspaceName, ld.Spec.SharedALBMainDomain).GetDeployment(ld.GetSpecName())

		} else {
			ld.Status.Endpoint.ExternalEndpoint = "https://" + domainname.New(ld.Spec.WorkspaceName, ld.Spec.RootDomain).GetDeployment(ld.GetSpecName())
		}
	}
	return r.Status().Update(ctx, ld)
}

func transitionState(replicas, readyReplicas int32, state leptonaiv1alpha1.LeptonDeploymentState) leptonaiv1alpha1.LeptonDeploymentState {
	if replicas == 0 && readyReplicas == 0 { // TODO: figure out a better state for zero size deployment??
		return leptonaiv1alpha1.LeptonDeploymentStateNotReady
	}

	if replicas > 0 && replicas == readyReplicas {
		return leptonaiv1alpha1.LeptonDeploymentStateRunning
	}
	switch state {
	case leptonaiv1alpha1.LeptonDeploymentStateUnknown:
		// State unknown means api-server just created the LD spec, so it is starting
		return leptonaiv1alpha1.LeptonDeploymentStateStarting
	case leptonaiv1alpha1.LeptonDeploymentStateStarting:
		// If starting and not ready, then still starting
		return leptonaiv1alpha1.LeptonDeploymentStateStarting
	default:
		if readyReplicas == 0 {
			// If not starting and no ready replicas, then not ready
			return leptonaiv1alpha1.LeptonDeploymentStateNotReady
		} else {
			// Otherwise, it is updating
			return leptonaiv1alpha1.LeptonDeploymentStateUpdating
		}
	}
}

func (r *LeptonDeploymentReconciler) finalize(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment) error {
	if err := r.deletePV(ctx, ld); err != nil && !apierrors.IsNotFound(err) {
		return err
	}
	ld.SetFinalizers(goutil.RemoveString(ld.GetFinalizers(), leptonaiv1alpha1.DeletionFinalizerName))
	return r.Update(ctx, ld)
}

func (r *LeptonDeploymentReconciler) createOrUpdateDeployment(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) (*appsv1.Deployment, error) {
	expectedDeployment, err := r.createDeployment(ctx, ld, or)
	if err != nil {
		return nil, err
	}
	existingDeployment := &appsv1.Deployment{}
	err = r.Client.Get(ctx, req.NamespacedName, existingDeployment)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return nil, err
		}

		goutil.Logger.Infow("creating a new leptonDeployment",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		err = r.Client.Create(ctx, expectedDeployment)
		if err != nil {
			return nil, err
		}
		goutil.Logger.Infow("created a new leptonDeployment",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		return expectedDeployment, nil
	} else {
		if compareAndPatchDeployment(existingDeployment, expectedDeployment) {
			goutil.Logger.Infow("Skipping updating the deployment: already up-to-date",
				"namespace", req.Namespace,
				"name", req.Name,
			)
			return existingDeployment, nil
		}

		goutil.Logger.Infow("updating an existing leptonDeployment",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if err := r.Client.Update(ctx, existingDeployment); err != nil {
			return nil, err
		}
		goutil.Logger.Infow("updated an existing leptonDeployment",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		return existingDeployment, nil
	}

}

func (r *LeptonDeploymentReconciler) createOrUpdateService(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) (*corev1.Service, error) {
	expectedService := newService(ld).createService(or)
	namespacedName := types.NamespacedName{
		Namespace: req.Namespace,
		Name:      service.ServiceName(ld.GetSpecName()),
	}
	existingService := &corev1.Service{}
	err := r.Client.Get(ctx, namespacedName, existingService)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return nil, err
		}

		goutil.Logger.Infow("creating a new service",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if err := r.Client.Create(ctx, expectedService); err != nil {
			return nil, err
		}
		goutil.Logger.Infow("created a new service",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		return expectedService, nil
	} else {
		if compareAndPatchService(existingService, expectedService) {
			goutil.Logger.Infow("Skipping updating the service: already up-to-date",
				"namespace", req.Namespace,
				"name", req.Name,
			)
			return existingService, nil
		}

		goutil.Logger.Infow("updating an existing service",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if err := r.Client.Update(ctx, existingService); err != nil {
			return nil, err
		}
		goutil.Logger.Infow("updated an existing service",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		return existingService, nil
	}
}

func (r *LeptonDeploymentReconciler) createOrUpdateIngress(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) error {
	if err := r.createOrUpdateHeaderBasedIngress(ctx, req, ld, or); err != nil {
		return err
	}
	if err := r.createOrUpdateHostBasedIngress(ctx, req, ld, or); err != nil {
		return err
	}
	return nil
}

func (r *LeptonDeploymentReconciler) createOrUpdateHeaderBasedIngress(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) error {
	expectedIngress := newIngress(ld).createHeaderBasedDeploymentIngress(or)
	namespacedName := types.NamespacedName{
		Namespace: req.Namespace,
		Name:      ingress.IngressNameForHeaderBased(ld.GetSpecName()),
	}
	existingIngress := &networkingv1.Ingress{}
	err := r.Client.Get(ctx, namespacedName, existingIngress)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}

		goutil.Logger.Infow("creating a new header based ingress",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if err := r.Client.Create(ctx, expectedIngress); err != nil {
			return err
		}
		goutil.Logger.Infow("created a new header based ingress",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	} else {
		if compareAndPatchIngress(existingIngress, expectedIngress) {
			goutil.Logger.Infow("Skipping updating the header-based ingress: already up-to-date",
				"namespace", req.Namespace,
				"name", req.Name,
			)
			return nil
		}

		goutil.Logger.Infow("updating an existing header based ingress",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if err := r.Client.Update(ctx, existingIngress); err != nil {
			return err
		}
		goutil.Logger.Infow("updated an existing header based ingress",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	}
	return nil
}

func (r *LeptonDeploymentReconciler) createOrUpdateHostBasedIngress(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) error {
	expectedIngress := newIngress(ld).createHostBasedDeploymentIngress(or)
	namespacedName := types.NamespacedName{
		Namespace: req.Namespace,
		Name:      ingress.IngressNameForHostBased(ld.GetSpecName()),
	}
	existingIngress := &networkingv1.Ingress{}
	err := r.Client.Get(ctx, namespacedName, existingIngress)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}

		if expectedIngress == nil {
			return nil
		}

		goutil.Logger.Infow("creating a new host based ingress",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if err := r.Client.Create(ctx, expectedIngress); err != nil {
			return err
		}
		goutil.Logger.Infow("created a new host based ingress",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	} else {
		if expectedIngress == nil {
			goutil.Logger.Infow("deleting an existing host based ingress",
				"namespace", req.Namespace,
				"name", req.Name,
			)
			return r.Client.Delete(ctx, existingIngress)
		}

		if compareAndPatchIngress(existingIngress, expectedIngress) {
			goutil.Logger.Infow("Skipping updating the host-based ingress: already up-to-date",
				"namespace", req.Namespace,
				"name", req.Name,
			)
			return nil
		}

		goutil.Logger.Infow("updating an existing host based ingress",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if err := r.Client.Update(ctx, existingIngress); err != nil {
			return err
		}
		goutil.Logger.Infow("updated an existing host based ingress",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	}
	return nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *LeptonDeploymentReconciler) SetupWithManager(mgr ctrl.Manager) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := mgr.GetFieldIndexer().IndexField(ctx, &corev1.Pod{}, "status.phase", func(rawObj client.Object) []string {
		pod := rawObj.(*corev1.Pod)
		return []string{string(pod.Status.Phase)}
	}); err != nil {
		return err
	}

	hd := handler.EnqueueRequestForOwner(mgr.GetScheme(),
		mgr.GetRESTMapper(),
		&leptonaiv1alpha1.LeptonDeployment{},
		handler.OnlyControllerOwner())
	return ctrl.NewControllerManagedBy(mgr).
		For(&leptonaiv1alpha1.LeptonDeployment{}).
		Watches(&appsv1.Deployment{}, hd).
		Watches(&corev1.Service{}, hd).
		Watches(&networkingv1.Ingress{}, hd).
		Watches(&corev1.PersistentVolumeClaim{}, hd).
		Watches(&corev1.PersistentVolume{}, hd).
		Complete(r)
}

func (r *LeptonDeploymentReconciler) createDeployment(ctx context.Context, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) (*appsv1.Deployment, error) {
	deployment := newDeploymentNvidia(ld).createDeployment(or)

	for i, v := range ld.Spec.Mounts {
		pvname := getPVName(ld.Namespace, ld.GetSpecName(), i)
		pvcname := getPVCName(ld.Namespace, ld.GetSpecName(), i)

		err := k8s.CreatePV(ctx, pvname, ld.Spec.EFSID+":"+v.Path+":"+ld.Spec.EFSAccessPointID)
		if err != nil && !apierrors.IsAlreadyExists(err) {
			return nil, err
		}

		goutil.Logger.Infow("created a new pv",
			"namespace", ld.Namespace,
			"name", ld.Name,
			"pvname", pvname,
		)
		err = k8s.CreatePVC(ctx, ld.Namespace, pvcname, pvname, or)
		if err != nil && !apierrors.IsAlreadyExists(err) {
			return nil, err
		}
		goutil.Logger.Infow("created a new pvc",
			"namespace", ld.Namespace,
			"name", ld.Name,
			"pvcname", pvcname,
		)
	}

	return deployment, nil
}

func (r *LeptonDeploymentReconciler) deletePV(ctx context.Context, ld *leptonaiv1alpha1.LeptonDeployment) error {
	for i := range ld.Spec.Mounts {
		pvname := getPVName(ld.Namespace, ld.GetSpecName(), i)

		goutil.Logger.Infow("deleting a pv",
			"namespace", ld.Namespace,
			"name", ld.Name,
			"pvname", pvname,
		)
		err := k8s.DeletePV(ctx, pvname)
		if err != nil && !apierrors.IsNotFound(err) {
			return err
		}
		goutil.Logger.Infow("deleted a pv",
			"namespace", ld.Namespace,
			"name", ld.Name,
			"pvname", pvname,
		)
	}
	return nil
}

func (r *LeptonDeploymentReconciler) createOrUpdateLoadBalancerRules(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []*gloocore.Metadata_OwnerReference) error {
	if err := r.createOrUpdateHeaderBasedLoadBalancerRules(ctx, req, ld, or); err != nil {
		return err
	}
	if err := r.createOrUpdateHostBasedLoadBalancerRules(ctx, req, ld, or); err != nil {
		return err
	}
	if err := r.createOrUpdateGlooUpstream(ctx, req, ld, or); err != nil {
		return err
	}
	return nil
}

func (r *LeptonDeploymentReconciler) createOrUpdateHeaderBasedLoadBalancerRules(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []*gloocore.Metadata_OwnerReference) error {
	expectedRouteTable := createHeaderBasedDeploymentRouteTable(ld, or)
	existingRouteTable, err := r.GlooClients.RouteTableClient.Read(ld.Namespace, createRouteTableName(ld), soloclients.ReadOpts{Ctx: ctx})
	if err != nil {
		if !glooerrors.IsNotExist(err) {
			return fmt.Errorf("failed to get RouteTable, error is not IsNotExist: %w", err)
		}

		goutil.Logger.Infow("creating a new header based routeTable",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if _, err := r.GlooClients.RouteTableClient.Write(expectedRouteTable, soloclients.WriteOpts{Ctx: ctx}); err != nil {
			return fmt.Errorf("failed to create new RouteTable: %w", err)
		}
		goutil.Logger.Infow("created a new header based routeTable",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	} else {
		if compareAndPatchRouteTable(existingRouteTable, expectedRouteTable) {
			goutil.Logger.Infow("Skipping updating the gloo route table: already up-to-date",
				"namespace", req.Namespace,
				"name", req.Name,
			)
			return nil
		}

		goutil.Logger.Infow("updating an existing header based routeTable",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if _, err := r.GlooClients.RouteTableClient.Write(existingRouteTable, soloclients.WriteOpts{Ctx: ctx, OverwriteExisting: true}); err != nil {
			return fmt.Errorf("failed to update existing RouteTable: %w", err)
		}
		goutil.Logger.Infow("updated an existing header based routeTable",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	}
	return nil
}

func (r *LeptonDeploymentReconciler) createOrUpdateHostBasedLoadBalancerRules(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []*gloocore.Metadata_OwnerReference) error {
	expectedVirtualService := createHostBasedDeploymentVirtualService(ld, or)
	existingVirtualService, err := r.GlooClients.VirtualServiceClient.Read(ld.Namespace, createDeploymentVirtualServiceName(ld), soloclients.ReadOpts{Ctx: ctx})
	if err != nil {
		if !glooerrors.IsNotExist(err) {
			return fmt.Errorf("failed to get VirtualService, error is not IsNotExist: %w", err)
		}

		goutil.Logger.Infow("creating a new host based virtual service",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if _, err := r.GlooClients.VirtualServiceClient.Write(expectedVirtualService, soloclients.WriteOpts{Ctx: ctx}); err != nil {
			return fmt.Errorf("failed to create new VirtualService: %w", err)
		}
		goutil.Logger.Infow("created a new host based virtual service",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	} else {
		if compareAndPatchVirtualService(existingVirtualService, expectedVirtualService) {
			goutil.Logger.Infow("Skipping updating the gloo virtual service: already up-to-date",
				"namespace", req.Namespace,
				"name", req.Name,
			)
			return nil
		}

		goutil.Logger.Infow("updating an existing host based virtual service",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if _, err := r.GlooClients.VirtualServiceClient.Write(existingVirtualService, soloclients.WriteOpts{Ctx: ctx, OverwriteExisting: true}); err != nil {
			return fmt.Errorf("failed to update existing VirtualService: %w", err)
		}
		goutil.Logger.Infow("updated an existing host based virtual service",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	}
	return nil
}

func (r *LeptonDeploymentReconciler) createOrUpdateGlooUpstream(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []*gloocore.Metadata_OwnerReference) error {
	expectedUpstream := createGlooUpstream(ld, or)
	existingUpstream, err := r.GlooClients.UpstreamClient.Read(ld.Namespace, createGlooUpstreamName(ld), soloclients.ReadOpts{Ctx: ctx})
	if err != nil {
		if !glooerrors.IsNotExist(err) {
			return fmt.Errorf("failed to get upstream, error is not IsNotExist: %w", err)
		}

		goutil.Logger.Infow("creating a new upstream",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if _, err := r.GlooClients.UpstreamClient.Write(expectedUpstream, soloclients.WriteOpts{Ctx: ctx}); err != nil {
			return fmt.Errorf("failed to create new upstream: %w", err)
		}
		goutil.Logger.Infow("created a new upstream",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	} else {
		if compareAndPatchGlooUpstream(existingUpstream, expectedUpstream) {
			goutil.Logger.Infow("Skipping updating the gloo upstream: already up-to-date",
				"namespace", req.Namespace,
				"name", req.Name,
			)
			return nil
		}

		goutil.Logger.Infow("updating an existing upstream",
			"namespace", req.Namespace,
			"name", req.Name,
		)
		if _, err := r.GlooClients.UpstreamClient.Write(existingUpstream, soloclients.WriteOpts{Ctx: ctx, OverwriteExisting: true}); err != nil {
			return fmt.Errorf("failed to update existing upstream: %w", err)
		}
		goutil.Logger.Infow("updated an existing upstream",
			"namespace", req.Namespace,
			"name", req.Name,
		)
	}
	return nil
}
