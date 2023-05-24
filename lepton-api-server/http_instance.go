package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/api"
	prometheusv1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"

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

	deploymentMapRWLock.RLock()
	metadata := deploymentById[duuid]
	deploymentMapRWLock.RUnlock()
	if metadata == nil {
		c.JSON(http.StatusNotFound, gin.H{"code": ErrorCodeInvalidParameterValue, "message": "deployment " + duuid + " does not exist."})
		return
	}

	deployment, err := clientset.AppsV1().Deployments(deploymentNamespace).Get(context.TODO(), metadata.Name, metav1.GetOptions{})
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to get deployment " + metadata.Name + ": " + err.Error()})
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
		c.JSON(http.StatusBadRequest, gin.H{"code": ErrorCodeInternalFailure, "message": "failed to get pods for deployment " + metadata.Name + ": " + err.Error()})
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

	tenMinutesInSeconds := int64(10 * 60)
	tenMBInBytes := int64(10 * 1024 * 1024)
	// TODO: support other log options
	logOptions := &corev1.PodLogOptions{
		Container:    mainContainerName,
		Follow:       true,
		SinceSeconds: &tenMinutesInSeconds,
		LimitBytes:   &tenMBInBytes,
	}
	req := clientset.CoreV1().Pods(deploymentNamespace).GetLogs(id, logOptions)
	podLogs, err := req.Stream(context.Background())
	// TODO: check if the error is pod not found, which can be user/web interface error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "cannot get pod logs for " + id + ": " + err.Error()})
		return
	}
	defer podLogs.Close()

	_, err = io.Copy(c.Writer, podLogs)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "cannot stream pod logs for " + id + ": " + err.Error()})
		return
	}
}

func instanceMemoryUsageHandler(c *gin.Context) {
	// get the memory usage for the past 1 hour
	result, err := queryPodMetrics("container_memory_usage_bytes{pod=\"" + c.Param("id") + "\", container=\"main-container\"}[1h]")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error executing query: " + err.Error()})
		return
	}

	data, err := cleanPrometheusQueryResult(result, "memory_usage", "")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error parsing query result: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, data)
}

func instanceMemoryTotalHandler(c *gin.Context) {
	// get the memory limit for the past 1 hour
	result, err := queryPodMetrics("container_spec_memory_limit_bytes{pod=\"" + c.Param("id") + "\", container=\"main-container\"}[1h]")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error executing query: " + err.Error()})
		return
	}

	data, err := cleanPrometheusQueryResult(result, "memory_total", "")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error parsing query result: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, data)
}

func instanceCPUUtilHandler(c *gin.Context) {
	// get the CPU Util over 2 min windows for the past 1 hour
	query := fmt.Sprintf(
		"(sum(rate(container_cpu_usage_seconds_total{pod=\"%s\", container=\"main-container\"}[2m])) / "+
			"sum(container_spec_cpu_quota{pod=\"%[1]s\", container=\"main-container\"}/container_spec_cpu_period{pod=\"%[1]s\", container=\"main-container\"}))[1h:1m]",
		c.Param("id"),
	)
	result, err := queryPodMetrics(query)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error executing query: " + err.Error()})
		return
	}

	data, err := cleanPrometheusQueryResult(result, "cpu_util", "")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error parsing query result: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, data)
}

func instanceQPSHandler(c *gin.Context) {
	// get the QPS over 2 min windows for the past 1 hour
	result, err := queryPodMetrics("sum by (handler) (rate(http_requests_total{kubernetes_pod_name=\"" + c.Param("id") + "\"}[2m]))[1h:1m]")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error executing query: " + err.Error()})
		return
	}

	data, err := cleanPrometheusQueryResult(result, "qps", "handler")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error parsing query result: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, data)
}

func instanceLatencyHandler(c *gin.Context) {
	result, err := queryPodMetrics("histogram_quantile(0.90, sum(increase(http_request_duration_seconds_bucket{kubernetes_pod_name=\"" + c.Param("id") + "\"}[2m])) by (le, handler))[1h:1m]")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error executing query: " + err.Error()})
		return
	}

	data, err := cleanPrometheusQueryResult(result, "latency_p90", "handler")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error parsing query result: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, data)
}

func cleanPrometheusQueryResult(result model.Value, name, keep string) ([]map[string]interface{}, error) {
	bytes, err := json.Marshal(result)
	if err != nil {
		return nil, err
	}
	// JSON decoding
	var data []map[string]interface{}
	if err := json.Unmarshal(bytes, &data); err != nil {
		return nil, err
	}

	// Remove fields in the "metrics" section except for "__name__"
	for _, item := range data {
		if metric, ok := item["metric"].(map[string]interface{}); ok {
			for key := range metric {
				if key != "__name__" && key != keep {
					delete(metric, key)
				}
			}
			if metric["__name__"] != nil {
				metric["name"] = metric["__name__"]
				delete(metric, "__name__")
			}
			if len(name) != 0 {
				metric["name"] = name
			}
		}
	}

	return data, nil
}

func queryPodMetrics(query string) (model.Value, error) {
	// Create an HTTP client
	client, err := api.NewClient(api.Config{
		Address: prometheusURL,
		Client:  &http.Client{Timeout: 10 * time.Second},
	})
	if err != nil {
		fmt.Println("Error creating client:", err)
		return nil, err
	}

	// Create a Prometheus API client
	promAPI := prometheusv1.NewAPI(client)
	result, warnings, err := promAPI.Query(context.Background(), query, time.Now())
	if len(warnings) > 0 {
		fmt.Println("Warnings received:", warnings)
	}

	return result, err
}
