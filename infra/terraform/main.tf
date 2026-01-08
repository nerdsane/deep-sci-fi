# Deep Sci-Fi AWS Infrastructure
# Main Terraform Configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get available AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Random suffix for unique bucket names
resource "random_id" "suffix" {
  byte_length = 4
}

# ============================================================================
# Networking Module
# ============================================================================
module "networking" {
  source = "./modules/networking"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = "10.0.0.0/16"
  azs          = slice(data.aws_availability_zones.available.names, 0, 2)
}

# ============================================================================
# Secrets Module
# ============================================================================
module "secrets" {
  source = "./modules/secrets"

  project_name      = var.project_name
  environment       = var.environment
  db_password       = var.db_password
  anthropic_api_key = var.anthropic_api_key
  openai_api_key    = var.openai_api_key
  google_api_key    = var.google_api_key
}

# ============================================================================
# IAM Module
# ============================================================================
module "iam" {
  source = "./modules/iam"

  project_name   = var.project_name
  environment    = var.environment
  aws_region     = var.aws_region
  aws_account_id = data.aws_caller_identity.current.account_id
  secrets_arns   = module.secrets.secret_arns
}

# ============================================================================
# Database Module
# ============================================================================
module "database" {
  source = "./modules/database"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  db_password        = var.db_password
  db_instance_class  = var.db_instance_class

  depends_on = [module.networking]
}

# ============================================================================
# Storage Module
# ============================================================================
module "storage" {
  source = "./modules/storage"

  project_name  = var.project_name
  environment   = var.environment
  random_suffix = random_id.suffix.hex
}

# ============================================================================
# Compute Module (ECS, ALB, ECR)
# ============================================================================
module "compute" {
  source = "./modules/compute"

  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  vpc_id             = module.networking.vpc_id
  public_subnet_ids  = module.networking.public_subnet_ids
  private_subnet_ids = module.networking.private_subnet_ids

  ecs_execution_role_arn = module.iam.ecs_execution_role_arn
  ecs_task_role_arn      = module.iam.ecs_task_role_arn

  db_host     = module.database.db_endpoint
  db_name     = module.database.db_name
  db_username = module.database.db_username

  db_password_secret_arn       = module.secrets.db_password_secret_arn
  anthropic_api_key_secret_arn = module.secrets.anthropic_api_key_secret_arn
  openai_api_key_secret_arn    = module.secrets.openai_api_key_secret_arn
  google_api_key_secret_arn    = module.secrets.google_api_key_secret_arn

  s3_assets_bucket = module.storage.assets_bucket_name
  cloudfront_domain = module.storage.cloudfront_domain

  ecs_cpu           = var.ecs_cpu
  ecs_memory        = var.ecs_memory
  ecs_desired_count = var.ecs_desired_count

  depends_on = [module.networking, module.iam, module.secrets]
}

# ============================================================================
# Security Group Rule: Allow ECS to access RDS
# (Created separately to avoid circular dependency)
# ============================================================================
resource "aws_security_group_rule" "rds_from_ecs" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.compute.ecs_security_group_id
  security_group_id        = module.database.db_security_group_id
  description              = "PostgreSQL from ECS"
}
