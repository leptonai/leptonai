locals {
  non_lepton_managed_namespace_selector = "has(projectcalico.org/name) && projectcalico.org/name not in {\"default\", \"kube-system\", \"cert-manager\", \"calico-system\", \"calico-apiserver\", \"external-dns\", \"gpu-operator\", \"prometheus\", \"grafana\", \"lepton-system\"}"
}

resource "kubernetes_manifest" "allow_external" {
  manifest = {
    apiVersion = "projectcalico.org/v3"
    kind       = "GlobalNetworkPolicy"

    metadata = {
      name = "allow-external-policy"
    }

    spec = {
      namespaceSelector = local.non_lepton_managed_namespace_selector

      types = ["Egress"]

      egress = [
        {
          action = "Allow"

          destination = {
            nets = ["${module.vpc.vpc_cidr_block}"]
          }
        }
      ]
    }
  }

  depends_on = [helm_release.calico]
}

resource "kubernetes_manifest" "allow_system_as_dest_policy" {
  manifest = {
    apiVersion = "projectcalico.org/v3"
    kind       = "GlobalNetworkPolicy"

    metadata = {
      name = "allow-system-as-dest-policy"
    }

    spec = {
      namespaceSelector = local.non_lepton_managed_namespace_selector

      types = ["Egress"]

      egress = [
        {
          action = "Allow"

          destination = {
            namespaceSelector = "has(projectcalico.org/name) && projectcalico.org/name in {\"default\", \"kube-system\", \"external-dns\", \"lepton-system\", \"prometheus\"}"
          }
        }
      ]
    }
  }

  depends_on = [helm_release.calico]
}

resource "kubernetes_manifest" "allow_kube_apiserver_policy" {
  manifest = {
    apiVersion = "projectcalico.org/v3"
    kind       = "GlobalNetworkPolicy"

    metadata = {
      name = "allow-kube-apiserver-policy"
    }

    spec = {
      namespaceSelector = local.non_lepton_managed_namespace_selector

      types    = ["Egress"]
      selector = "app in {\"lepton-deployment-operator\", \"lepton-api-server\"}"

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
