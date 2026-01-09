# Deep Sci-Fi AWS Infrastructure Variables

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "deep-sci-fi"
}

# Database
variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

# ECS
variable "ecs_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 1024 # 1 vCPU
}

variable "ecs_memory" {
  description = "ECS task memory (MB)"
  type        = number
  default     = 2048 # 2 GB
}

variable "ecs_desired_count" {
  description = "Number of ECS tasks"
  type        = number
  default     = 1
}

# API Keys (sensitive)
variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_api_key" {
  description = "Google API key for Gemini (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

# ============================================================================
# EC2 Configuration (for single-instance deployment)
# ============================================================================

variable "key_pair_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
  default     = "deep-sci-fi-key"
}

variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "ec2_volume_size" {
  description = "EC2 root volume size in GB"
  type        = number
  default     = 40
}

variable "ssh_cidr_blocks" {
  description = "CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict in production
}

variable "github_repo" {
  description = "GitHub repository URL for the project"
  type        = string
  default     = "https://github.com/nerdsane/deep-sci-fi.git"
}
