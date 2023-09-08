resource "null_resource" "delete_all_lepton_deployments_and_ingresses" {
  triggers = {
    region       = var.region
    cluster_name = local.cluster_name
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOD
aws eks update-kubeconfig --region ${self.triggers.region} --name ${self.triggers.cluster_name} --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig
kubectl --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig delete leptondeployments --all-namespaces --all
sleep 5
kubectl --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig delete ingress --all-namespaces --all
EOD
  }
}

# https://github.com/tigera/operator/issues/2031
resource "null_resource" "delete_calico_installation" {
  triggers = {
    helm_tigera  = helm_release.calico.status
    region       = var.region
    cluster_name = local.cluster_name
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
aws eks update-kubeconfig --region ${self.triggers.region} --name ${self.triggers.cluster_name} --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig
kubectl --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig delete installations.operator.tigera.io default
sleep 5
    EOT
  }
}
