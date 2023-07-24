package httpapi

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/leptonai/lepton/go-pkg/httperrors"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	leptonaiv1alpha1 "github.com/leptonai/lepton/lepton-deployment-operator/api/v1alpha1"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/api"
	prometheusv1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
)

type MonitorningHandler struct {
	Handler
}

func (h *MonitorningHandler) ReplicaMemoryUtil(c *gin.Context) {
	// get the memory util for the past 1 hour
	query := fmt.Sprintf("(container_memory_usage_bytes{pod=\"%s\", container=\"main-container\"} / "+
		"container_spec_memory_limit_bytes{pod=\"%[1]s\", container=\"main-container\"})[1h:1m]", c.Param("rid"))
	result, err := h.queryMetrics(c, query, "memory_util", "")
	if err != nil {
		goutil.Logger.Errorw("failed to get memory util",
			"operation", "getReplicaMemoryUtil",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaMemoryUsage(c *gin.Context) {
	// get the memory usage bytes for the past 1 hour
	query := "container_memory_usage_bytes{pod=\"" + c.Param("rid") + "\", container=\"main-container\"}[1h:1m]"
	result, err := h.queryAndScaleMetrics(c, query, "memory_usage_in_MiB", "", 1.0/1024/1024)
	if err != nil {
		goutil.Logger.Errorw("failed to get memory usage",
			"operation", "getReplicaMemoryUsage",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaMemoryTotal(c *gin.Context) {
	// get the memory limit bytes for the past 1 hour
	query := "container_spec_memory_limit_bytes{pod=\"" + c.Param("rid") + "\", container=\"main-container\"}[1h:1m]"
	result, err := h.queryAndScaleMetrics(c, query, "memory_total_in_MiB", "", 1.0/1024/1024)
	if err != nil {
		goutil.Logger.Errorw("failed to get memory total",
			"operation", "getReplicaMemoryTotal",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaCPUUtil(c *gin.Context) {
	// get the average CPU Util over 2 min windows for the past 1 hour
	query := fmt.Sprintf(
		"(sum(rate(container_cpu_usage_seconds_total{pod=\"%s\", container=\"main-container\"}[2m])) / "+
			"sum(container_spec_cpu_quota{pod=\"%[1]s\", container=\"main-container\"}/container_spec_cpu_period{pod=\"%[1]s\", container=\"main-container\"}))[1h:1m]",
		c.Param("rid"),
	)
	result, err := h.queryMetrics(c, query, "cpu_util", "")
	if err != nil {
		goutil.Logger.Errorw("failed to get cpu util",
			"operation", "getReplicaCPUUtil",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaFastAPIQPS(c *gin.Context) {
	handlers, err := h.listHandlersForPrometheusQuery(c, c.Param("did"))
	if err != nil {
		handlers = "/.*"
	}
	// get the average QPS over 2 min windows for the past 1 hour, gouped by request paths
	query := "sum(rate(http_requests_total{kubernetes_pod_name=\"" + c.Param("rid") + "\", handler=~\"" + handlers + "\"}[2m]))[1h:1m]"
	result, err := h.queryMetrics(c, query, "all", "")
	if err != nil {
		goutil.Logger.Errorw("failed to get QPS",
			"operation", "getReplicaFastAPIQPS",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaFastAPILatency(c *gin.Context) {
	handlers, err := h.listHandlersForPrometheusQuery(c, c.Param("did"))
	if err != nil {
		handlers = "/.*"
	}
	// get the 90-percentile latency over 2 min windows for the past 1 hour, gouped by request paths
	query := "histogram_quantile(0.90, sum(increase(http_request_duration_seconds_bucket{kubernetes_pod_name=\"" + c.Param("rid") + "\", handler=~\"" + handlers + "\"}[2m])) by (le))[1h:1m]"
	result, err := h.queryMetrics(c, query, "all", "")
	if err != nil {
		goutil.Logger.Errorw("failed to get latency",
			"operation", "getReplicaFastAPILatency",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaFastAPIQPSByPath(c *gin.Context) {
	handlers, err := h.listHandlersForPrometheusQuery(c, c.Param("did"))
	if err != nil {
		handlers = "/.*"
	}
	// get the average QPS over 2 min windows for the past 1 hour, gouped by request paths
	query := "sum by (handler) (rate(http_requests_total{kubernetes_pod_name=\"" + c.Param("rid") + "\", handler=~\"" + handlers + "\"}[2m]))[1h:1m]"
	result, err := h.queryMetrics(c, query, "qps", "handler")
	if err != nil {
		goutil.Logger.Errorw("failed to get QPS",
			"operation", "getReplicaFastAPIQPSByPath",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaFastAPILatencyByPath(c *gin.Context) {
	handlers, err := h.listHandlersForPrometheusQuery(c, c.Param("did"))
	if err != nil {
		handlers = "/.*"
	}
	// get the 90-percentile latency over 2 min windows for the past 1 hour, gouped by request paths
	query := "histogram_quantile(0.90, sum(increase(http_request_duration_seconds_bucket{kubernetes_pod_name=\"" + c.Param("rid") + "\", handler=~\"" + handlers + "\"}[2m])) by (le, handler))[1h:1m]"
	result, err := h.queryMetrics(c, query, "latency_p90", "handler")
	if err != nil {
		goutil.Logger.Errorw("failed to get latency",
			"operation", "getReplicaFastAPILatencyByPath",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) DeploymentFastAPIQPS(c *gin.Context) {
	handlers, err := h.listHandlersForPrometheusQuery(c, c.Param("did"))
	if err != nil {
		handlers = "/.*"
	}
	// get the inference QPS over 2 min windows for the past 1 hour
	query := "sum(rate(http_requests_total{kubernetes_pod_label_lepton_deployment_id=\"" + c.Param("did") + "\", handler=~\"" + handlers + "\"}[2m]))[1h:1m]"
	result, err := h.queryMetrics(c, query, "all", "")
	if err != nil {
		goutil.Logger.Errorw("failed to get QPS",
			"operation", "getDeploymentFastAPIQPS",
			"deployment", c.Param("did"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) DeploymentFastAPILatency(c *gin.Context) {
	handlers, err := h.listHandlersForPrometheusQuery(c, c.Param("did"))
	if err != nil {
		handlers = "/.*"
	}
	// get the 90-percentile inference latency over 2 min windows for the past 1 hour
	query := "histogram_quantile(0.90, sum(increase(http_request_duration_seconds_bucket{kubernetes_pod_label_lepton_deployment_id=\"" + c.Param("did") + "\", handler=~\"" + handlers + "\"}[2m])) by (le))[1h:1m]"
	result, err := h.queryMetrics(c, query, "all", "")
	if err != nil {
		goutil.Logger.Errorw("failed to get latency",
			"operation", "getDeploymentFastAPILatency",
			"deployment", c.Param("did"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) DeploymentFastAPIQPSByPath(c *gin.Context) {
	handlers, err := h.listHandlersForPrometheusQuery(c, c.Param("did"))
	if err != nil {
		handlers = "/.*"
	}
	// get the QPS over 2 min windows for the past 1 hour, gouped by request paths
	query := "sum by (handler) (rate(http_requests_total{kubernetes_pod_label_lepton_deployment_id=\"" + c.Param("did") + "\", handler=~\"" + handlers + "\"}[2m]))[1h:1m]"
	result, err := h.queryMetrics(c, query, "qps", "handler")
	if err != nil {
		goutil.Logger.Errorw("failed to get QPS",
			"operation", "getDeploymentFastAPIQPSByPath",
			"deployment", c.Param("did"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) DeploymentFastAPILatencyByPath(c *gin.Context) {
	handlers, err := h.listHandlersForPrometheusQuery(c, c.Param("did"))
	if err != nil {
		handlers = "/.*"
	}
	// get the 90-percentile latency over 2 min windows for the past 1 hour, gouped by request paths
	query := "histogram_quantile(0.90, sum(increase(http_request_duration_seconds_bucket{kubernetes_pod_label_lepton_deployment_id=\"" + c.Param("did") + "\", handler=~\"" + handlers + "\"}[2m])) by (le, handler))[1h:1m]"
	result, err := h.queryMetrics(c, query, "latency_p90", "handler")
	if err != nil {
		goutil.Logger.Errorw("failed to get latency",
			"operation", "getDeploymentFastAPILatencyByPath",
			"deployment", c.Param("did"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaGPUMemoryUtil(c *gin.Context) {
	// get the GPU memory util for the past 1 hour
	query := "DCGM_FI_DEV_MEM_COPY_UTIL{pod=\"" + c.Param("rid") + "\"}[1h:1m]"
	result, err := h.queryMetrics(c, query, "gpu_memory_util", "gpu")
	if err != nil {
		goutil.Logger.Errorw("failed to get GPU memory util",
			"operation", "getReplicaGPUMemoryUtil",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaGPUUtil(c *gin.Context) {
	// get the GPU util for the past 1 hour
	query := "DCGM_FI_DEV_GPU_UTIL{pod=\"" + c.Param("rid") + "\"}[1h:1m]"
	result, err := h.queryMetrics(c, query, "gpu_util", "gpu")
	if err != nil {
		goutil.Logger.Errorw("failed to get GPU util",
			"operation", "getReplicaGPUUtil",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaGPUMemoryUsage(c *gin.Context) {
	// get the GPU memory usage in MB for the past 1 hour
	query := "DCGM_FI_DEV_FB_USED{pod=\"" + c.Param("rid") + "\"}[1h:1m]"
	result, err := h.queryMetrics(c, query, "gpu_memory_usage_in_MiB", "gpu")
	if err != nil {
		goutil.Logger.Errorw("failed to get GPU memory usage",
			"operation", "getReplicaGPUMemoryUsage",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) ReplicaGPUMemoryTotal(c *gin.Context) {
	// get the GPU total memory in MB for the past 1 hour
	query := "(DCGM_FI_DEV_FB_USED{pod=\"" + c.Param("rid") + "\"} + DCGM_FI_DEV_FB_FREE{pod=\"" + c.Param("rid") + "\"})[1h:1m]"
	result, err := h.queryMetrics(c, query, "gpu_memory_total_in_MiB", "gpu")
	if err != nil {
		goutil.Logger.Errorw("failed to get GPU total memory",
			"operation", "getReplicaGPUMemoryTotal",
			"replica", c.Param("rid"),
			"error", err,
		)

		c.JSON(http.StatusInternalServerError, gin.H{"code": httperrors.ErrorCodeInternalFailure, "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *MonitorningHandler) cleanAndScalePrometheusQueryResult(result model.Value, name, keep string, scale float64) ([]map[string]interface{}, error) {
	bytes, err := json.Marshal(result)
	if err != nil {
		return nil, err
	}
	// JSON decoding
	data := make([]map[string]interface{}, 0)
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
		if values, ok := item["values"].([]interface{}); ok {
			for _, value := range values {
				if v, ok := value.([]interface{}); ok {
					if len(v) == 2 {
						if v[1] == "NaN" || v[1] == "Inf" || v[1] == "-Inf" || v[1] == "+Inf" {
							v[1] = 0
						}
						switch v[1].(type) {
						case int:
							v[1] = int(float64(v[1].(int)) * scale)
						case float64:
							v[1] = v[1].(float64) * scale
						case string:
							vv, err := strconv.ParseFloat(v[1].(string), 64)
							if err == nil {
								v[1] = vv * scale
							}
						}
					}
				}
			}
		}
	}

	return data, nil
}

func (h *MonitorningHandler) queryPodMetrics(ctx context.Context, query string) (model.Value, error) {
	// Create an HTTP client
	client, err := api.NewClient(api.Config{
		Address: h.prometheusURL,
		Client:  &http.Client{Timeout: 10 * time.Second},
	})
	if err != nil {
		return nil, err
	}

	// Create a Prometheus API client
	promAPI := prometheusv1.NewAPI(client)
	result, warnings, err := promAPI.Query(ctx, query, time.Now())
	if len(warnings) > 0 {
		goutil.Logger.Warnw("Warnings received from Prometheus",
			"operation", "queryPodMetrics",
			"warnings", warnings,
		)
	}

	return result, err
}

func (h *MonitorningHandler) queryMetrics(ctx context.Context, query, name, keep string) ([]map[string]interface{}, error) {
	return h.queryAndScaleMetrics(ctx, query, name, keep, 1)
}

func (h *MonitorningHandler) queryAndScaleMetrics(ctx context.Context, query, name, keep string, scale float64) ([]map[string]interface{}, error) {
	result, err := h.queryPodMetrics(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("error executing query: %v", err)
	}

	data, err := h.cleanAndScalePrometheusQueryResult(result, name, keep, scale)
	if err != nil {
		return nil, fmt.Errorf("error parsing query result: %v", err)
	}

	return data, nil
}

func (h *MonitorningHandler) getPhotonHTTPPaths(ph *leptonaiv1alpha1.Photon) []string {
	b, err := ph.Spec.OpenAPISchema.MarshalJSON()
	if err != nil {
		return nil
	}
	var schema map[string]interface{}
	json.Unmarshal(b, &schema)
	pathMap := schema["paths"].(map[string]interface{})
	pathArray := make([]string, 0, len(pathMap))
	for p := range pathMap {
		pathArray = append(pathArray, p)
	}
	return pathArray
}

func (h *MonitorningHandler) listHandlersForPrometheusQuery(ctx context.Context, did string) (string, error) {
	ld, err := h.ldDB.Get(ctx, did)
	if err != nil {
		return "", fmt.Errorf("deployment " + did + " does not exist.")
	}
	ph, err := h.phDB.Get(ctx, ld.Spec.PhotonID)
	if err != nil {
		return "", fmt.Errorf("photon " + ld.Spec.PhotonID + " does not exist.")
	}
	paths := h.getPhotonHTTPPaths(ph)
	if len(paths) == 0 {
		return "", fmt.Errorf("photon " + ld.Spec.PhotonID + " does not have any handlers.")
	}
	return strings.Join(paths, "|"), nil
}
