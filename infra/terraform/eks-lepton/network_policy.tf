locals {
  workspace_namespace_selector = "has(projectcalico.org/name) && (projectcalico.org/name starts with \"ws-\") && !(projectcalico.org/name ends with \"sys\")"
  lepton_component_selector    = "app in {\"lepton-deployment-operator\", \"lepton-api-server\"}"
}

resource "kubernetes_manifest" "allow_user_pod_to_external" {
  manifest = {
    apiVersion = "projectcalico.org/v3"
    kind       = "GlobalNetworkPolicy"

    metadata = {
      name = "allow-external-policy"
    }

    spec = {
      namespaceSelector = local.workspace_namespace_selector

      types = ["Egress"]

      egress = [
        {
          action = "Allow"

          destination = {
            notNets = ["${module.vpc.vpc_cidr_block}"]
          }
        }
      ]
    }
  }

  depends_on = [helm_release.calico]
}

resource "kubernetes_manifest" "allow_user_pod_to_kube_dns" {
  manifest = {
    apiVersion = "projectcalico.org/v3"
    kind       = "GlobalNetworkPolicy"

    metadata = {
      name = "allow-user-pod-to-kube-dns"
    }

    spec = {
      namespaceSelector = local.workspace_namespace_selector

      types = ["Egress"]

      egress = [
        {
          action = "Allow"

          destination = {
            services = {
              name      = "kube-dns"
              namespace = "kube-system"
            }
          }
        }
      ]
    }
  }

  depends_on = [helm_release.calico]
}

resource "kubernetes_manifest" "allow_node_to_all_policy" {
  manifest = {
    apiVersion = "projectcalico.org/v3"
    kind       = "GlobalNetworkPolicy"

    metadata = {
      name = "allow-node-to-all-policy"
    }

    spec = {
      types = ["Egress"]

      selector = "has(kubernetes-host)"

      egress = [
        {
          action = "Allow"

          destination = {
            nets = ["0.0.0.0/0"]
          }
        }
      ]
    }
  }

  depends_on = [helm_release.calico]
}

resource "kubernetes_manifest" "allow_lepton_to_systems_as_dest_policy" {
  manifest = {
    apiVersion = "projectcalico.org/v3"
    kind       = "GlobalNetworkPolicy"

    metadata = {
      name = "allow-system-as-dest-policy"
    }

    spec = {
      namespaceSelector = local.workspace_namespace_selector
      selector          = local.lepton_component_selector


      types = ["Egress"]

      egress = [
        {
          action = "Allow"

          destination = {
            namespaceSelector = "has(projectcalico.org/name) && projectcalico.org/name in {\"default\", \"kube-system\", \"external-dns\", \"ws-${var.cluster_name}sys\", \"kube-prometheus-stack\"}"
          }
        }
      ]
    }
  }

  depends_on = [helm_release.calico]
}

resource "kubernetes_manifest" "allow_lepton_to_k8s_service_policy" {
  manifest = {
    apiVersion = "projectcalico.org/v3"
    kind       = "GlobalNetworkPolicy"

    metadata = {
      name = "allow-kube-apiserver-policy"
    }

    spec = {
      namespaceSelector = local.workspace_namespace_selector
      selector          = local.lepton_component_selector

      types = ["Egress"]

      egress = [
        {
          action = "Allow"

          destination = {
            services = {
              name      = "kubernetes"
              namespace = "default"
            }
          }
        }
      ]
    }
  }

  depends_on = [helm_release.calico]
}
