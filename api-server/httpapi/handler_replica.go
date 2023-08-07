package httpapi

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	"github.com/leptonai/lepton/go-pkg/k8s"
	goutil "github.com/leptonai/lepton/go-pkg/util"

	"github.com/gin-gonic/gin"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	restclient "k8s.io/client-go/rest"
	"sigs.k8s.io/controller-runtime/pkg/client/config"
)

type ReplicaHandler struct {
	Handler
}

const mainContainerName = "main-container"

func (h *ReplicaHandler) List(c *gin.Context) {
	did := c.Param("did")
	clientset := k8s.MustInitK8sClientSet()

	ld, err := h.ldDB.Get(c, did)
	if apierrors.IsNotFound(err) {
		goutil.Logger.Debugw("deployment not found",
			"operation", "getReplicas",
			"deployment", did,
		)
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeResourceNotFound, "message": "deployment " + did + " not found"})
		return
	}
	if err != nil {
		goutil.Logger.Errorw("failed to get deployment",
			"operation", "getReplicas",
			"deployment", did,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get deployment " + did + ": " + err.Error()})
		return
	}

	deployment, err := clientset.AppsV1().Deployments(h.namespace).Get(c, ld.GetSpecName(), metav1.GetOptions{})
	if err != nil {
		goutil.Logger.Errorw("failed to get deployment",
			"operation", "getReplicas",
			"deployment", did,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get deployment " + ld.GetSpecName() + ": " + err.Error()})
		return
	}

	labels := deployment.Spec.Selector.MatchLabels
	labelSelector := ""
	for key, value := range labels {
		if labelSelector != "" {
			labelSelector += ","
		}
		labelSelector += fmt.Sprintf("%s=%s", key, value)
	}

	podList, err := clientset.CoreV1().Pods(h.namespace).List(c, metav1.ListOptions{LabelSelector: labelSelector})
	if err != nil {
		goutil.Logger.Errorw("failed to get replicas for deployment",
			"operation", "getReplicas",
			"deployment", did,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get replicas for deployment " + ld.GetSpecName() + ": " + err.Error()})
		return
	}

	is := make([]Replica, 0, len(podList.Items))
	for _, pod := range podList.Items {
		if pod.Status.Phase != corev1.PodRunning && pod.Status.Phase != corev1.PodPending {
			goutil.Logger.Warnw("pod is not (running, pending), skipping",
				"operation", "getReplicas",
				"deployment", did,
				"pod", pod.Name,
				"phase", pod.Status.Phase,
				"reason", pod.Status.Reason,
			)
			continue
		}
		is = append(is, Replica{ID: pod.Name})
	}

	c.JSON(http.StatusOK, is)
}

func (h *ReplicaHandler) Shell(c *gin.Context) {
	inClusterConfig, err := config.GetConfig()
	if err != nil {
		goutil.Logger.Errorw("failed to get in cluster config for shell",
			"operation", "shell",
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to get in cluster config for shell"})
		return
	}

	rid := c.Param("rid")
	httpClient, err := restclient.HTTPClientFor(inClusterConfig)
	if err != nil {
		goutil.Logger.Errorw("failed to create client for shell",
			"operation", "shell",
			"replica", rid,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create client for shell"})
		return
	}

	targetURL, err := url.Parse(inClusterConfig.Host)
	if err != nil {
		goutil.Logger.Errorw("failed to parse host for shell",
			"operation", "shell",
			"replica", rid,
			"url", inClusterConfig.Host,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "failed to create connection for shell"})
		return
	}

	// Create a reverse proxy
	// TODO: use a pool of reverse proxies
	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.Transport = httpClient.Transport

	r := c.Request
	// Close the forward request regardless of the action from the client.
	defer r.Body.Close()

	// delete our custom authorization header so that we don't forward it and override k8s auth
	r.Header.Del("Authorization")
	r.Host = targetURL.Host
	r.URL.Host = targetURL.Host
	r.URL.Scheme = targetURL.Scheme
	r.URL.Path = "/api/v1/namespaces/" + h.namespace + "/pods/" + rid + "/exec"
	q := r.URL.Query()
	q.Set("container", mainContainerName)
	q.Set("command", "/bin/bash")
	q.Set("stdout", "true")
	q.Set("stdin", "true")
	q.Set("stderr", "true")
	q.Set("tty", "true")
	r.URL.RawQuery = q.Encode()

	proxy.ServeHTTP(c.Writer, r)
}

func (h *ReplicaHandler) Log(c *gin.Context) {
	rid := c.Param("rid")

	clientset := k8s.MustInitK8sClientSet()

	tailLines := int64(10000)
	tenMBInBytes := int64(10 * 1024 * 1024)
	// TODO: support other log options
	logOptions := &corev1.PodLogOptions{
		Container:  mainContainerName,
		Follow:     true,
		TailLines:  &tailLines,
		LimitBytes: &tenMBInBytes,
	}
	req := clientset.CoreV1().Pods(h.namespace).GetLogs(rid, logOptions)
	podLogs, err := req.Stream(c)
	if apierrors.IsNotFound(err) {
		c.JSON(http.StatusNotFound, gin.H{"code": httperrors.ErrorCodeInvalidRequest, "message": "replica " + rid + " not found"})
		return
	}
	if k8s.IsPodInitializingError(err) {
		c.JSON(http.StatusPreconditionFailed, gin.H{"code": httperrors.ErrorCodeValidationError, "message": "replica " + rid + " is initializing"})
		return
	}
	if err != nil {
		goutil.Logger.Errorw("failed to get logs for replica",
			"operation", "getLogs",
			"replica", rid,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "cannot get logs for replica " + rid + ": " + err.Error()})
		return
	}
	defer podLogs.Close()

	buffer := make([]byte, 4096)
	for {
		n := 0
		n, err = podLogs.Read(buffer)
		if err != nil {
			break
		}
		_, err = c.Writer.Write(buffer[:n])
		if err != nil {
			break
		}
		c.Writer.Flush()
	}

	if err != nil && err != io.EOF && err != context.Canceled {
		goutil.Logger.Errorw("failed to stream logs for replica",
			"operation", "getLogs",
			"replica", rid,
			"error", err,
		)
		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": "cannot stream logs for replica " + rid + ": " + err.Error()})
		return
	}
}
