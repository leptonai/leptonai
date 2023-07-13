resource "helm_release" "kube_prometheus_stack" {
  name             = "kube-prometheus-stack"
  namespace        = "kube-prometheus-stack"
  create_namespace = true
  chart            = "kube-prometheus-stack"
  repository       = "https://prometheus-community.github.io/helm-charts"

  # TODO: set managed prometheus remote writer?
  # https://prometheus.io/docs/prometheus/latest/configuration/configuration/
  # https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/values.yaml
  values = [yamlencode({
    prometheus = {
      enabled = true
      ingress = {
        # NOTE: to just use service
        #
        # e.g.,
        # <service-name>.<namespace>.svc.cluster.local:<service-port>
        # http://kube-prometheus-stack-prometheus.kube-prometheus-stack.svc.cluster.local:9090
        #
        # e.g.,
        # k -n kube-prometheus-stack port-forward prometheus-kube-prometheus-stack-prometheus-0 3000:9090
        # for local testing
        enabled = false
      }
      prometheusSpec = {
        scrapeInterval = "15s"
        scrapeTimeout  = "4s"
        retention      = "24h"
        retentionSize  = "100GB"
        walCompression = true

        storageSpec = {
          volumeClaimTemplate = {
            spec = {
              storageClassName = "gp3"
              resources = {
                requests = {
                  storage = "200Gi"
                }
              }
            }
          }
        }

        # c.f., https://github.com/leptonai/lepton/pull/1369/files
        additionalScrapeConfigs = [
          {
            job_name = "lepton-deployment-pods"
            kubernetes_sd_configs = [
              {
                role = "pod"
              }
            ]
            relabel_configs = [
              {
                source_labels = ["__meta_kubernetes_pod_label_photon_id"]
                action        = "keep"
                regex         = ".+"
              },
              {
                source_labels = ["__meta_kubernetes_pod_label_lepton_deployment_id"]
                action        = "keep"
                regex         = ".+"
              },
              {
                source_labels = ["__meta_kubernetes_pod_label_photon_id"]
                target_label  = "kubernetes_pod_label_photon_id"
                action        = "replace"
              },
              {
                source_labels = ["__meta_kubernetes_pod_label_lepton_deployment_id"]
                target_label  = "kubernetes_pod_label_lepton_deployment_id"
                action        = "replace"
              },
              {
                source_labels = ["__meta_kubernetes_pod_name"]
                target_label  = "kubernetes_pod_name"
                action        = "replace"
              },
              {
                source_labels = ["__meta_kubernetes_namespace"]
                target_label  = "kubernetes_namespace"
                action        = "replace"
              },
            ]
          }
        ]
      }
    }
  })]
}
