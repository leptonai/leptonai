package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"

	"github.com/gin-gonic/gin"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	restclient "k8s.io/client-go/rest"
)

var (
	prometheusURL = ""
)

func instanceListHandler(c *gin.Context) {
	duuid := c.Param("uuid")
	clientset := mustInitK8sClientSet()

	ld := deploymentDB.GetByID(duuid)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "deployment " + duuid + " does not exist."})
		return
	}

	deployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Get(context.TODO(), ld.Name, metav1.GetOptions{})
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to get deployment " + ld.Name + ": " + err.Error()})
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

	podList, err := clientset.CoreV1().Pods(deploymentNamespace).List(context.TODO(), metav1.ListOptions{LabelSelector: labelSelector})
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to get pods for deployment " + ld.Name + ": " + err.Error()})
		return
	}

	is := make([]Instance, 0, len(podList.Items))
	for _, pod := range podList.Items {
		is = append(is, Instance{ID: pod.Name})
	}

	c.JSON(http.StatusOK, is)
}

func instanceShellHandler(c *gin.Context) {
	id := c.Param("id")
	_, config := mustInitK8sClientSetWithConfig()
	httpClient, err := restclient.HTTPClientFor(config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Failed to get the logging client"})
		return
	}

	targetURL, err := url.Parse(config.Host)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Bad logging URL"})
		return
	}

	// Create a reverse proxy
	// TODO: use a pool of reverse proxies
	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.Transport = httpClient.Transport

	r := c.Request
	r.Host = targetURL.Host
	r.URL.Host = targetURL.Host
	r.URL.Scheme = targetURL.Scheme
	r.URL.Path = "/api/v1/namespaces/default/pods/" + id + "/exec"
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

func instanceLogHandler(c *gin.Context) {
	id := c.Param("id")

	clientset := mustInitK8sClientSet()

	tailLines := int64(10000)
	tenMBInBytes := int64(10 * 1024 * 1024)
	// TODO: support other log options
	logOptions := &corev1.PodLogOptions{
		Container:  mainContainerName,
		Follow:     true,
		TailLines:  &tailLines,
		LimitBytes: &tenMBInBytes,
	}
	req := clientset.CoreV1().Pods(deploymentNamespace).GetLogs(id, logOptions)
	podLogs, err := req.Stream(context.Background())
	// TODO: check if the error is pod not found, which can be user/web interface error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "cannot get pod logs for " + id + ": " + err.Error()})
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

	if err != nil && err != io.EOF {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "cannot stream pod logs for " + id + ": " + err.Error()})
		return
	}
}
