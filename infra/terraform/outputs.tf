# Deep Sci-Fi AWS Infrastructure Outputs
# EC2 Deployment Mode

# ============================================================================
# Networking
# ============================================================================
output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
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
# EC2 Instance
# ============================================================================
output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = module.ec2.instance_id
}

output "ec2_public_ip" {
  description = "EC2 public IP (Elastic IP)"
  value       = module.ec2.public_ip
}

output "ec2_public_dns" {
  description = "EC2 public DNS"
  value       = module.ec2.public_dns
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = module.ec2.ssh_command
}

output "service_urls" {
  description = "Direct service URLs"
  value       = module.ec2.service_urls
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
    Deep Sci-Fi EC2 Deployment Complete!
    ============================================

    EC2 Instance:     ${module.ec2.public_ip}
    SSH Command:      ${module.ec2.ssh_command}

    Service URLs (direct access):
    - Web App:        http://${module.ec2.public_ip}:3000
    - Letta UI:       http://${module.ec2.public_ip}:4000
    - Letta API:      http://${module.ec2.public_ip}:8283
    - WebSocket:      ws://${module.ec2.public_ip}:8284

    Assets CDN:       https://${module.storage.cloudfront_domain}

    Next Steps:
    1. SSH into instance: ${module.ec2.ssh_command}
    2. Edit .env with API keys: nano ~/deep-sci-fi/.env
    3. Start services: docker-compose -f docker-compose.prod.yml up -d
    4. Configure GitHub secrets for CI/CD:
       - EC2_HOST: ${module.ec2.public_ip}
       - EC2_SSH_KEY: (your private key)

    ============================================
  EOT
}

# ============================================================================
# DISABLED: ECS Outputs
# Uncomment when using ECS deployment
# ============================================================================

# output "database_endpoint" {
#   description = "RDS database endpoint"
#   value       = module.database.db_endpoint
# }

# output "database_url" {
#   description = "Full database connection URL"
#   value       = "postgresql://${module.database.db_username}:${var.db_password}@${module.database.db_endpoint}:5432/${module.database.db_name}"
#   sensitive   = true
# }

# output "ecr_repository_url" {
#   description = "ECR repository URL for Letta server"
#   value       = module.compute.ecr_repository_url
# }

# output "alb_dns_name" {
#   description = "Application Load Balancer DNS name"
#   value       = module.compute.alb_dns_name
# }

# output "ecs_cluster_name" {
#   description = "ECS cluster name"
#   value       = module.compute.ecs_cluster_name
# }

# output "ecs_service_name" {
#   description = "ECS service name"
#   value       = module.compute.ecs_service_name
# }
