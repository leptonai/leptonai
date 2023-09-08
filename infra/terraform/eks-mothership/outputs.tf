output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ids attached to the cluster control plane"
  value       = module.eks.cluster_security_group_id
}

output "region" {
  description = "AWS region"
  value       = var.region
}

output "cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = module.eks.cluster_name
}

output "oidc" {
  description = "value of the OpenID Connect issuer URL"
  value       = module.eks.cluster_oidc_issuer_url
}

output "oidc_id" {
  description = "value of the OpenID Connect provider ID"
  value       = substr(module.eks.cluster_oidc_issuer_url, length(module.eks.cluster_oidc_issuer_url) - 32, 32)
}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}
