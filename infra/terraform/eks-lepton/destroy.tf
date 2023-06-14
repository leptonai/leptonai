resource "null_resource" "delete_all_lepton_deployments_and_ingresses" {
  triggers = {
    region       = var.region
    cluster_name = local.cluster_name
  }

  provisioner "local-exec" {
    command = <<-EOC
aws eks update-kubeconfig --region ${self.triggers.region} --name ${self.triggers.cluster_name} --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig
EOC
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOD
kubectl --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig delete leptondeployments --all-namespaces --all
sleep 5
kubectl --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig delete ingress --all-namespaces --all
EOD
  }
}

resource "null_resource" "delete_prometheus" {
  triggers = {
    region       = var.region
    cluster_name = local.cluster_name
  }

  provisioner "local-exec" {
    command = <<-EOC
aws eks update-kubeconfig --region ${self.triggers.region} --name ${self.triggers.cluster_name} --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig
EOC
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOD
kubectl --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig delete ns prometheus --grace-period=0 --force
EOD
  }
}

resource "null_resource" "delete_grafana" {
  triggers = {
    region       = var.region
    cluster_name = local.cluster_name
  }

  provisioner "local-exec" {
    command = <<-EOC
aws eks update-kubeconfig --region ${self.triggers.region} --name ${self.triggers.cluster_name} --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig
EOC
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOD
kubectl --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig delete ns grafana --grace-period=0 --force
EOD
  }
}
