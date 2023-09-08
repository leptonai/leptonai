output "access_points" {
  description = "Map of access points created and their attributes"
  value       = local.efs_exists ? module.efs[0].access_points["non_root"] : null
}
