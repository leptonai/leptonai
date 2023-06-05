package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"

	"github.com/leptonai/lepton/lepton-api-server/httpapi"
	"github.com/leptonai/lepton/lepton-api-server/util"

	"github.com/gin-gonic/gin"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	restclient "k8s.io/client-go/rest"
)

const mainContainerName = "main-container"

func instanceListHandler(c *gin.Context) {
	did := c.Param("did")
	clientset := util.MustInitK8sClientSet()

	ld := deploymentDB.GetByID(did)
	if ld == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": httpapi.ErrorCodeInvalidParameterValue, "message": "deployment " + did + " does not exist."})
		return
	}

	deployment, err := clientset.AppsV1().Deployments(*namespaceFlag).Get(context.TODO(), ld.GetName(), metav1.GetOptions{})
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to get deployment " + ld.GetName() + ": " + err.Error()})
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

	podList, err := clientset.CoreV1().Pods(*namespaceFlag).List(context.TODO(), metav1.ListOptions{LabelSelector: labelSelector})
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "failed to get pods for deployment " + ld.GetName() + ": " + err.Error()})
		return
	}

	is := make([]httpapi.Instance, 0, len(podList.Items))
	for _, pod := range podList.Items {
		is = append(is, httpapi.Instance{ID: pod.Name})
	}

	c.JSON(http.StatusOK, is)
}

func instanceShellHandler(c *gin.Context) {
	iid := c.Param("iid")
	_, config := util.MustInitK8sClientSetWithConfig()
	httpClient, err := restclient.HTTPClientFor(config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "Failed to get the logging client"})
		return
	}

	targetURL, err := url.Parse(config.Host)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "Bad logging URL"})
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
	r.URL.Path = "/api/v1/namespaces/" + *namespaceFlag + "/pods/" + iid + "/exec"
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
	iid := c.Param("iid")

	clientset := util.MustInitK8sClientSet()

	tailLines := int64(10000)
	tenMBInBytes := int64(10 * 1024 * 1024)
	// TODO: support other log options
	logOptions := &corev1.PodLogOptions{
		Container:  mainContainerName,
		Follow:     true,
		TailLines:  &tailLines,
		LimitBytes: &tenMBInBytes,
	}
	req := clientset.CoreV1().Pods(*namespaceFlag).GetLogs(iid, logOptions)
	podLogs, err := req.Stream(context.Background())
	// TODO: check if the error is pod not found, which can be user/web interface error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "cannot get pod logs for " + iid + ": " + err.Error()})
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
		c.JSON(http.StatusInternalServerError, gin.H{"code": httpapi.ErrorCodeInternalFailure, "message": "cannot stream pod logs for " + iid + ": " + err.Error()})
		return
	}
}
