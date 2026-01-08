# Deep Sci-Fi AWS Infrastructure Outputs

# ============================================================================
# Networking
# ============================================================================
output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

# ============================================================================
# Database
# ============================================================================
output "database_endpoint" {
  description = "RDS database endpoint"
  value       = module.database.db_endpoint
}

output "database_url" {
  description = "Full database connection URL"
  value       = "postgresql://${module.database.db_username}:${var.db_password}@${module.database.db_endpoint}:5432/${module.database.db_name}"
  sensitive   = true
}

# ============================================================================
# Storage
# ============================================================================
output "assets_bucket_name" {
  description = "S3 bucket name for assets"
  value       = module.storage.assets_bucket_name
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain for assets"
  value       = module.storage.cloudfront_domain
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.storage.cloudfront_distribution_id
}

# ============================================================================
# Compute
# ============================================================================
output "ecr_repository_url" {
  description = "ECR repository URL for Letta server"
  value       = module.compute.ecr_repository_url
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.compute.alb_dns_name
}

output "api_endpoint" {
  description = "API endpoint URL"
  value       = "http://${module.compute.alb_dns_name}"
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.compute.ecs_cluster_name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = module.compute.ecs_service_name
}

# ============================================================================
# Deployment Info
# ============================================================================
output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "deployment_info" {
  description = "Deployment summary"
  value = <<-EOT

    ============================================
    Deep Sci-Fi AWS Deployment Complete!
    ============================================

    API Endpoint:     http://${module.compute.alb_dns_name}
    Assets CDN:       https://${module.storage.cloudfront_domain}
    ECR Repository:   ${module.compute.ecr_repository_url}

    Database Host:    ${module.database.db_endpoint}

    Next Steps:
    1. Build and push Letta image: ./scripts/deploy.sh build-letta
    2. Run migrations: ./scripts/deploy.sh migrate-db
    3. Migrate data: ./scripts/deploy.sh migrate-data
    4. Update ECS: ./scripts/deploy.sh update-ecs

    ============================================
  EOT
}
