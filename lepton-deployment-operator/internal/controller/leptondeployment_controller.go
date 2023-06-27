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
	"strconv"
	"sync"

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
	"sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/source"

	domainname "github.com/leptonai/lepton/go-pkg/domain-name"
	"github.com/leptonai/lepton/go-pkg/k8s"
	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	"github.com/leptonai/lepton/go-pkg/k8s/service"
	"github.com/leptonai/lepton/go-pkg/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"
)

// LeptonDeploymentReconciler reconciles a LeptonDeployment object
type LeptonDeploymentReconciler struct {
	client.Client
	Scheme *runtime.Scheme

	chMap     map[types.NamespacedName]chan struct{}
	chMapLock sync.Mutex
	wg        sync.WaitGroup
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
	log.Log.Info("Reconciling LeptonDeployment:" + req.NamespacedName.String())

	r.chMapLock.Lock()
	defer r.chMapLock.Unlock()
	if r.chMap == nil {
		r.chMap = make(map[types.NamespacedName]chan struct{})
	}
	if _, ok := r.chMap[req.NamespacedName]; !ok {
		ch := make(chan struct{}, 100)
		go r.watch(ctx, req, ch)
		r.chMap[req.NamespacedName] = ch
	}
	r.chMap[req.NamespacedName] <- struct{}{}

	return ctrl.Result{}, nil
}

// watch watches for changes to LeptonDeployment resources
func (r *LeptonDeploymentReconciler) watch(ctx context.Context, req ctrl.Request, ch chan struct{}) {
	// Listen to the chan for LeptonDeployment updates
	for range ch {
		log.Log.Info("Being poked for LeptonDeployment " + req.NamespacedName.String())
		drainChan(ch) // Drain chan to avoid unnecessary reconciles
		ld, err := r.getLeptonDeployment(ctx, req)
		if err != nil {
			log.Log.Info("Failed to get LeptonDeployment " + req.NamespacedName.String() + ": " + err.Error())
			r.wg.Add(1)
			go backoffAndRetry(&r.wg, ch)
			continue
		}
		// Add our finalizer if it does not exist
		if ld != nil && !util.ContainsString(ld.GetFinalizers(), leptonaiv1alpha1.DeletionFinalizerName) {
			ld.SetFinalizers(append(ld.GetFinalizers(), leptonaiv1alpha1.DeletionFinalizerName))
			if err := r.Update(ctx, ld); err != nil {
				log.Log.Error(err, "Failed to update add finalizer to LeptonDeployment: "+req.NamespacedName.String()+": "+err.Error())
				r.wg.Add(1)
				go backoffAndRetry(&r.wg, ch)
				continue
			}
		}
		// Check the deployment status
		if err := r.updateDeploymentStatus(ctx, req, ld); err != nil {
			log.Log.Error(err, "Failed to update LeptonDeployment status: "+req.NamespacedName.String()+": "+err.Error())
			r.wg.Add(1)
			go backoffAndRetry(&r.wg, ch)
			continue
		}
		// LeptonDeployment has been deleted or marked for deletion
		if ld == nil || !ld.DeletionTimestamp.IsZero() {
			log.Log.Info("LeptonDeployment " + req.NamespacedName.String() + " marked for deletion, destroying resources")
			if r.destroy(ctx, req, ld) {
				return
			}
			continue
		}
		// Reconcile resources
		if err := r.createOrUpdateResources(ctx, req, ld); err != nil {
			r.wg.Add(1)
			go backoffAndRetry(&r.wg, ch)
			continue
		}
	}
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
	// Attaches all resources to the service using owner reference, so that they
	// are deleted when the service is deleted. The only exception is the PV,
	// which has to be deleted separately.
	service, err := r.createOrUpdateService(ctx, req, ld, []metav1.OwnerReference{*ldOr})
	if err != nil {
		log.Log.Error(err, "Failed to create or update Service: "+req.NamespacedName.String())
		return err
	}
	svcOr := getOwnerRefFromService(service)
	_, err = r.createOrUpdateDeployment(ctx, req, ld, []metav1.OwnerReference{*ldOr, *svcOr})
	if err != nil {
		log.Log.Error(err, "Failed to create or update Deployment: "+req.NamespacedName.String())
		return err
	}
	if err := r.createOrUpdateIngress(ctx, req, ld, []metav1.OwnerReference{*ldOr, *svcOr}); err != nil {
		log.Log.Error(err, "Failed to create or update Ingress: "+req.NamespacedName.String())
		return err
	}
	return nil
}

func (r *LeptonDeploymentReconciler) updateDeploymentStatus(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment) error {
	if ld == nil {
		return nil
	}
	if !ld.DeletionTimestamp.IsZero() {
		ld.Status.State = leptonaiv1alpha1.LeptonDeploymentStateDeleting
		ld.Status.Endpoint.InternalEndpoint = ""
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
		ld.Status.Endpoint.InternalEndpoint = "http://" + ld.GetSpecName() + "." + ld.Namespace + ".svc.cluster.local:" + strconv.Itoa(service.Port)
		ld.Status.Endpoint.ExternalEndpoint = "https://" + domainname.New(ld.Spec.WorkspaceName, ld.Spec.RootDomain).GetDeployment(ld.GetSpecName())
	}
	return r.Status().Update(ctx, ld)
}

func transitionState(replicas, readyReplicas int32, state leptonaiv1alpha1.LeptonDeploymentState) leptonaiv1alpha1.LeptonDeploymentState {
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

func (r *LeptonDeploymentReconciler) finalize(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment) bool {
	if err := r.deleteService(ctx, ld); err != nil && !apierrors.IsNotFound(err) {
		log.Log.Error(err, "Failed to delete service: "+req.NamespacedName.String())
		r.wg.Add(1)
		go backoffAndRetry(&r.wg, r.chMap[req.NamespacedName])
		return false
	}
	if err := r.deletePV(ctx, ld); err != nil && !apierrors.IsNotFound(err) {
		log.Log.Error(err, "Failed to delete pv: "+req.NamespacedName.String())
		r.wg.Add(1)
		go backoffAndRetry(&r.wg, r.chMap[req.NamespacedName])
		return false
	}
	ld.SetFinalizers(util.RemoveString(ld.GetFinalizers(), leptonaiv1alpha1.DeletionFinalizerName))
	if err := r.Update(ctx, ld); err != nil {
		log.Log.Error(err, "Failed to remove finalizer from LeptonDeployment: "+req.NamespacedName.String())
		r.wg.Add(1)
		go backoffAndRetry(&r.wg, r.chMap[req.NamespacedName])
		return false
	}
	return true
}

func (r *LeptonDeploymentReconciler) destroy(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment) bool {
	// Delete resources
	if ld != nil {
		if !r.finalize(ctx, req, ld) {
			return false
		}
	}
	// Remove the chan from the map when the function exits
	r.chMapLock.Lock()
	ch := r.chMap[req.NamespacedName]
	delete(r.chMap, req.NamespacedName)
	r.chMapLock.Unlock()
	go func() {
		for range ch {
			// Drain the channel
		}
	}()
	r.wg.Wait()
	close(ch)
	return true
}

func (r *LeptonDeploymentReconciler) createOrUpdateDeployment(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) (*appsv1.Deployment, error) {
	deployment := &appsv1.Deployment{}
	err := r.Client.Get(ctx, req.NamespacedName, deployment)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return nil, err
		}
		log.Log.Info("Deployment not found, creating a new one: " + req.NamespacedName.String())
		deployment, err = r.createDeployment(ctx, ld, or)
		if err != nil {
			return nil, err
		}
	} else {
		log.Log.Info("Deployment found, patching it: " + req.NamespacedName.String())
		newDeploymentNvidia(ld).patchDeployment(deployment)
		if err := r.Client.Update(ctx, deployment); err != nil {
			return nil, err
		}
	}
	return deployment, nil
}

func (r *LeptonDeploymentReconciler) createOrUpdateService(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) (*corev1.Service, error) {
	namespacedName := types.NamespacedName{
		Namespace: req.Namespace,
		Name:      service.ServiceName(ld.GetSpecName()),
	}
	service := &corev1.Service{}
	err := r.Client.Get(ctx, namespacedName, service)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return nil, err
		}
		log.Log.Info("Service not found, creating a new one: " + req.NamespacedName.String())
		service = newService(ld).createService(or)
		if err := r.Client.Create(ctx, service); err != nil {
			return nil, err
		}
	} else {
		log.Log.Info("Service found, patching it: " + req.NamespacedName.String())
		service = newService(ld).createService(or)
		if err := r.Client.Update(ctx, service); err != nil {
			return nil, err
		}
	}
	return service, nil
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
	namespacedName := types.NamespacedName{
		Namespace: req.Namespace,
		Name:      ingress.IngressNameForHeaderBased(ld.GetSpecName()),
	}
	ingress := &networkingv1.Ingress{}
	err := r.Client.Get(ctx, namespacedName, ingress)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		ingress = newIngress(ld).createHeaderBasedDeploymentIngress(or)
		if ingress != nil {
			log.Log.Info("Header based Ingress not found, creating a new one: " + req.NamespacedName.String())
			if err := r.Client.Create(ctx, ingress); err != nil {
				return err
			}
		}
	} else {
		ingress = newIngress(ld).createHeaderBasedDeploymentIngress(or)
		if ingress != nil {
			log.Log.Info("Header based Ingress found, patching it: " + req.NamespacedName.String())
			if err := r.Client.Update(ctx, ingress); err != nil {
				return err
			}
		}
	}
	return nil
}

func (r *LeptonDeploymentReconciler) createOrUpdateHostBasedIngress(ctx context.Context, req ctrl.Request, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) error {
	namespacedName := types.NamespacedName{
		Namespace: req.Namespace,
		Name:      ingress.IngressNameForHostBased(ld.GetSpecName()),
	}
	ingress := &networkingv1.Ingress{}
	err := r.Client.Get(ctx, namespacedName, ingress)
	if err != nil {
		if !apierrors.IsNotFound(err) {
			return err
		}
		log.Log.Info("Host based Ingress not found, creating a new one: " + req.NamespacedName.String())
		ingress = newIngress(ld).createHostBasedDeploymentIngress(or)
		if ingress != nil {
			if err := r.Client.Create(ctx, ingress); err != nil {
				return err
			}
		}
	} else {
		ingress = newIngress(ld).createHostBasedDeploymentIngress(or)
		if ingress != nil {
			log.Log.Info("Host based Ingress found, patching it: " + req.NamespacedName.String())
			if err := r.Client.Update(ctx, ingress); err != nil {
				return err
			}
		}
	}
	return nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *LeptonDeploymentReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&leptonaiv1alpha1.LeptonDeployment{}).
		Watches(
			&source.Kind{Type: &appsv1.Deployment{}},
			&handler.EnqueueRequestForOwner{OwnerType: &leptonaiv1alpha1.LeptonDeployment{}},
		).
		Watches(
			&source.Kind{Type: &corev1.Service{}},
			&handler.EnqueueRequestForOwner{OwnerType: &leptonaiv1alpha1.LeptonDeployment{}},
		).
		Watches(
			&source.Kind{Type: &networkingv1.Ingress{}},
			&handler.EnqueueRequestForOwner{OwnerType: &leptonaiv1alpha1.LeptonDeployment{}},
		).
		Complete(r)
}

func (r *LeptonDeploymentReconciler) createDeployment(ctx context.Context, ld *leptonaiv1alpha1.LeptonDeployment, or []metav1.OwnerReference) (*appsv1.Deployment, error) {
	deployment := newDeploymentNvidia(ld).createDeployment(or)

	for i, v := range ld.Spec.Mounts {
		pvname := getPVName(ld.Namespace, ld.GetSpecName(), i)
		pvcname := getPVCName(ld.Namespace, ld.GetSpecName(), i)

		err := k8s.CreatePV(pvname, ld.Spec.EFSID+":"+v.Path)
		if err != nil && !apierrors.IsAlreadyExists(err) {
			return nil, err
		}
		err = k8s.CreatePVC(ld.Namespace, pvcname, pvname, or)
		if err != nil && !apierrors.IsAlreadyExists(err) {
			return nil, err
		}
	}

	err := r.Client.Create(ctx, deployment)
	if err != nil {
		return nil, err
	}
	return deployment, nil
}

func (r *LeptonDeploymentReconciler) deletePV(ctx context.Context, ld *leptonaiv1alpha1.LeptonDeployment) error {
	for i := range ld.Spec.Mounts {
		pvname := getPVName(ld.Namespace, ld.GetSpecName(), i)

		err := k8s.DeletePV(pvname)
		if err != nil && !apierrors.IsNotFound(err) {
			return err
		}
	}
	return nil
}

func (r *LeptonDeploymentReconciler) deleteService(ctx context.Context, ld *leptonaiv1alpha1.LeptonDeployment) error {
	service := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      ld.GetSpecName(),
			Namespace: ld.Namespace,
		},
	}
	return r.Client.Delete(ctx, service)
}
