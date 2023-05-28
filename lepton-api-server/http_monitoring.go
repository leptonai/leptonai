package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/api"
	prometheusv1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
)

func instanceMemoryUsageHandler(c *gin.Context) {
	// get the memory usage for the past 1 hour
	query := "container_memory_usage_bytes{pod=\"" + c.Param("id") + "\", container=\"main-container\"}[1h]"
	result, err := queryMetrics(query, "memory_usage", "")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func instanceMemoryTotalHandler(c *gin.Context) {
	// get the memory limit for the past 1 hour
	query := "container_spec_memory_limit_bytes{pod=\"" + c.Param("id") + "\", container=\"main-container\"}[1h]"
	result, err := queryMetrics(query, "memory_total", "")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func instanceCPUUtilHandler(c *gin.Context) {
	// get the CPU Util over 2 min windows for the past 1 hour
	query := fmt.Sprintf(
		"(sum(rate(container_cpu_usage_seconds_total{pod=\"%s\", container=\"main-container\"}[2m])) / "+
			"sum(container_spec_cpu_quota{pod=\"%[1]s\", container=\"main-container\"}/container_spec_cpu_period{pod=\"%[1]s\", container=\"main-container\"}))[1h:1m]",
		c.Param("id"),
	)
	result, err := queryMetrics(query, "cpu_util", "")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func instanceFastAPIQPSHandler(c *gin.Context) {
	handlers, err := listHandlersForPrometheusQuery(c.Param("uuid"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// get the QPS over 2 min windows for the past 1 hour
	query := "sum by (handler) (rate(http_requests_total{kubernetes_pod_name=\"" + c.Param("id") + "\", handler=~\"" + handlers + "\"}[2m]))[1h:1m]"
	result, err := queryMetrics(query, "qps", "handler")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func instanceFastAPILatencyHandler(c *gin.Context) {
	handlers, err := listHandlersForPrometheusQuery(c.Param("uuid"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	query := "histogram_quantile(0.90, sum(increase(http_request_duration_seconds_bucket{kubernetes_pod_name=\"" + c.Param("id") + "\", handler=~\"" + handlers + "\"}[2m])) by (le, handler))[1h:1m]"
	result, err := queryMetrics(query, "latency_p90", "handler")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func deploymentFastAPIQPSHandler(c *gin.Context) {
	handlers, err := listHandlersForPrometheusQuery(c.Param("uuid"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// get the QPS over 2 min windows for the past 1 hour
	query := "sum by (handler) (rate(http_requests_total{kubernetes_pod_label_deployment_id=\"" + c.Param("uuid") + "\", handler=~\"" + handlers + "\"}[2m]))[1h:1m]"
	result, err := queryMetrics(query, "qps", "handler")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func deploymentFastAPILatencyHandler(c *gin.Context) {
	handlers, err := listHandlersForPrometheusQuery(c.Param("uuid"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	query := "histogram_quantile(0.90, sum(increase(http_request_duration_seconds_bucket{kubernetes_pod_label_deployment_id=\"" + c.Param("uuid") + "\", handler=~\"" + handlers + "\"}[2m])) by (le, handler))[1h:1m]"
	result, err := queryMetrics(query, "latency_p90", "handler")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func instanceGPUMemoryUtilHandler(c *gin.Context) {
	query := "DCGM_FI_DEV_MEM_COPY_UTIL{pod=\"" + c.Param("id") + "\"}[1h]"
	result, err := queryMetrics(query, "gpu_memory_util", "gpu")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func instanceGPUUtilHandler(c *gin.Context) {
	query := "DCGM_FI_DEV_GPU_UTIL{pod=\"" + c.Param("id") + "\"}[1h]"
	result, err := queryMetrics(query, "gpu_util", "gpu")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func instanceGPUMemoryUsageHandler(c *gin.Context) {
	query := "DCGM_FI_DEV_FB_USED{pod=\"" + c.Param("id") + "\"}[1h]"
	result, err := queryMetrics(query, "gpu_memory_usage_in_MB", "gpu")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func instanceGPUMemoryTotalHandler(c *gin.Context) {
	query := "(DCGM_FI_DEV_FB_USED{pod=\"" + c.Param("id") + "\"} + DCGM_FI_DEV_FB_FREE{pod=\"" + c.Param("id") + "\"})[1h:1m]"
	result, err := queryMetrics(query, "gpu_memory_total_in_MB", "gpu")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
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

	// Remove fields in the "metrics" section except for "__name__" and keep
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

func queryMetrics(query, name, keep string) ([]map[string]interface{}, error) {
	result, err := queryPodMetrics(query)
	if err != nil {
		return nil, fmt.Errorf("error executing query: %v", err)
	}

	data, err := cleanPrometheusQueryResult(result, name, keep)
	if err != nil {
		return nil, fmt.Errorf("error parsing query result: %v", err)
	}

	return data, nil
}

func getPhotonHTTPPaths(ph *Photon) []string {
	pathMap := ph.OpenApiSchema["paths"].(map[string]interface{})
	pathArray := make([]string, 0, len(pathMap))
	for p := range pathMap {
		pathArray = append(pathArray, p)
	}
	return pathArray
}

func listHandlersForPrometheusQuery(uuid string) (string, error) {
	ld := deploymentDB.GetByID(uuid)
	if ld == nil {
		return "", fmt.Errorf("deployment " + uuid + " does not exist.")
	}
	ph := photonDB.GetByID(ld.PhotonID)
	if ph == nil {
		return "", fmt.Errorf("photon " + ld.PhotonID + " does not exist.")
	}
	paths := getPhotonHTTPPaths(ph)
	if len(paths) == 0 {
		return "", fmt.Errorf("photon " + ld.PhotonID + " does not have any handlers.")
	}
	return strings.Join(paths, "|"), nil
}
