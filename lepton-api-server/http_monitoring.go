package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/api"
	prometheusv1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
)

func instanceMemoryUsageHandler(c *gin.Context) {
	// get the memory usage for the past 1 hour
	query := "container_memory_usage_bytes{pod=\"" + c.Param("id") + "\", container=\"main-container\"}[1h]"
	queryMetricsHandler(c, query, "memory_usage", "")
}

func instanceMemoryTotalHandler(c *gin.Context) {
	// get the memory limit for the past 1 hour
	query := "container_spec_memory_limit_bytes{pod=\"" + c.Param("id") + "\", container=\"main-container\"}[1h]"
	queryMetricsHandler(c, query, "memory_total", "")
}

func instanceCPUUtilHandler(c *gin.Context) {
	// get the CPU Util over 2 min windows for the past 1 hour
	query := fmt.Sprintf(
		"(sum(rate(container_cpu_usage_seconds_total{pod=\"%s\", container=\"main-container\"}[2m])) / "+
			"sum(container_spec_cpu_quota{pod=\"%[1]s\", container=\"main-container\"}/container_spec_cpu_period{pod=\"%[1]s\", container=\"main-container\"}))[1h:1m]",
		c.Param("id"),
	)
	queryMetricsHandler(c, query, "cpu_util", "")
}

func instanceFastAPIQPSHandler(c *gin.Context) {
	// get the QPS over 2 min windows for the past 1 hour
	query := "sum by (handler) (rate(http_requests_total{kubernetes_pod_name=\"" + c.Param("id") + "\"}[2m]))[1h:1m]"
	queryMetricsHandler(c, query, "qps", "handler")
}

func instanceFastAPILatencyHandler(c *gin.Context) {
	query := "histogram_quantile(0.90, sum(increase(http_request_duration_seconds_bucket{kubernetes_pod_name=\"" + c.Param("id") + "\"}[2m])) by (le, handler))[1h:1m]"
	queryMetricsHandler(c, query, "latency_p90", "handler")
}

func deploymentFastAPIQPSHandler(c *gin.Context) {
	// get the QPS over 2 min windows for the past 1 hour
	query := "sum by (handler) (rate(http_requests_total{kubernetes_pod_label_deployment_id=\"" + c.Param("uuid") + "\"}[2m]))[1h:1m]"
	queryMetricsHandler(c, query, "qps", "handler")
}

func deploymentFastAPILatencyHandler(c *gin.Context) {
	query := "histogram_quantile(0.90, sum(increase(http_request_duration_seconds_bucket{kubernetes_pod_label_deployment_id=\"" + c.Param("uuid") + "\"}[2m])) by (le, handler))[1h:1m]"
	queryMetricsHandler(c, query, "latency_p90", "handler")
}

func instanceGPUMemoryUtilHandler(c *gin.Context) {
	query := "DCGM_FI_DEV_MEM_COPY_UTIL{pod=\"" + c.Param("id") + "\"}[1h]"
	queryMetricsHandler(c, query, "gpu_memory_util", "gpu")
}

func instanceGPUUtilHandler(c *gin.Context) {
	query := "DCGM_FI_DEV_GPU_UTIL{pod=\"" + c.Param("id") + "\"}[1h]"
	queryMetricsHandler(c, query, "gpu_util", "gpu")
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

func queryMetricsHandler(c *gin.Context, query, name, keep string) {
	result, err := queryPodMetrics(query)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error executing query: " + err.Error()})
		return
	}

	data, err := cleanPrometheusQueryResult(result, name, keep)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": ErrorCodeInternalFailure, "message": "Error parsing query result: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, data)
}
