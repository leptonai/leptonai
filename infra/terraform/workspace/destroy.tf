resource "null_resource" "delete_all_lepton_deployments" {
  triggers = {
    region       = var.region
    cluster_name = var.cluster_name
    namespace = var.namespace
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOD
aws eks update-kubeconfig --region ${self.triggers.region} --name ${self.triggers.cluster_name} --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig
kubectl --kubeconfig /tmp/${self.triggers.cluster_name}.kubeconfig -n ${self.triggers.namespace} delete leptondeployments --all
sleep 5
EOD
  }

  depends_on = [
    helm_release.lepton
   ]
}
